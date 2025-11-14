import dateutil
import pytz

import lxml
from openstates.scrape import Scraper, Event

# from openstates.exceptions import EmptyScrape
from utils.events import match_coordinates
from utils import LXMLMixin


class COEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("America/Denver")

    chamber_names = {"upper": "Senate", "lower": "House"}

    schedule_url = "https://leg.colorado.gov/schedule"

    def clean(self, text):
        if type(text) is list:
            return text[0].text_content().strip()
        return text.text_content().strip()

    def scrape(self):
        yield from self.scrape_upcoming_events()

        # TODO: past events aren't stable enough yet, but write a scraper to get
        # additional info when it's posted

    def scrape_upcoming_events(self):
        page = self.get(self.schedule_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(self.schedule_url)

        for parent_row in page.cssselect("div.interim-schedule-table"):
            start_date = self.clean(parent_row.cssselect("h3"))

            for row in parent_row.cssselect("tbody tr"):
                yield from self.scrape_event_row(row, start_date)

    def scrape_event_row(self, row: lxml.html.HtmlElement, start_day: str):
        start_time = self.clean(row.xpath("td[1]"))
        com_name = self.clean(row.xpath("td[2]"))
        location = self.clean(row.xpath("td[3]"))
        location = f"{location}, 200 E Colfax Ave, Denver, CO 80203"

        start = f"{start_day} {start_time}"
        start = dateutil.parser.parse(start, fuzzy=True)
        start = self._tz.localize(start)

        event = Event(com_name, start, location, status="tentative")

        event.add_committee(com_name)

        agenda_link = row.xpath("td[4]//a[contains(text(), 'Agenda')]")

        if agenda_link:
            agenda_url = agenda_link[0].xpath("@href")[0]
            event.add_document(
                "Agenda", agenda_url, media_type="text/html", classification="agenda"
            )

            self.scrape_agenda_page(event, agenda_url)
            event.add_source(agenda_url)

        pdf_agenda_link = row.xpath("td[4]//a[contains(text(), 'PDF')]")
        if pdf_agenda_link:
            pdf_agenda_url = pdf_agenda_link[0].xpath("@href")[0]
            event.add_document(
                "Agenda",
                pdf_agenda_url,
                media_type="application/pdf",
                classification="agenda",
            )

        match_coordinates(event, {"200 E Colfax": (39.7393, -104.9645)})

        event.add_source(self.schedule_url)

        yield event

    def scrape_agenda_page(self, event: Event, url: str):
        page = self.get(url).content
        page = lxml.html.fromstring(page)

        for row in page.cssselect("section.hearing-items-block tbody tr"):
            item = self.clean(row.xpath("td[1]"))
            event.add_agenda_item(item)
