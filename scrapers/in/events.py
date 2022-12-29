import pytz
import cloudscraper
import dateutil.parser
from datetime import date
import lxml.html
from openstates.scrape import Scraper, Event


class INEventScraper(Scraper):
    _tz = pytz.timezone("America/Indianapolis")
    scraper = cloudscraper.create_scraper()

    def scrape(self):
        list_url = (
            f"http://iga.in.gov/legislative/{date.today().year}/committees/standing"
        )
        page = self.scraper.get(list_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(list_url)

        for com_row in page.xpath('//li[contains(@class,"committee-item")]/a'):
            committee = com_row.text_content()
            url = com_row.xpath("@href")
            yield from self.scrape_committee_page(url, committee)

    def scrape_committee_page(self, url, name):
        page = self.scraper.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        com = page.xpath('//div[contains(@class, "pull-left span8")]/h1/text()')[
            0
        ].strip()
        event_objects = set()

        for row in page.xpath('//div[contains(@id, "agenda-item")]'):
            meta = row.xpath('div[contains(@class,"accordion-heading-agenda")]/a')[0]

            date = meta.xpath("text()")[0].strip()

            time_and_loc = meta.xpath("span/text()")[0].strip()
            time_and_loc = time_and_loc.split("\n")
            time = time_and_loc[0]
            # Indiana has a LOT of undefined times, stuff like "15 mins after adj. of elections"
            # so just remove the time component if it won't parse, and the user can go to the agenda
            try:
                when = dateutil.parser.parse(f"{date} {time}")
            except dateutil.parser._parser.ParserError:
                when = dateutil.parser.parse(date)
            when = self._tz.localize(when)

            if "cancelled" in time.lower():
                continue

            loc = time_and_loc[1]

            if not loc:
                loc = "See Agenda"

            com = com.replace("(S)", "Senate").replace("(H)", "House")

            event_name = f"{name}#{com}#{when}"
            if event_name in event_objects:
                self.warning(f"Duplicate event {event_name} found. Skipping")
                continue

            event = Event(
                name=com,
                start_date=when,
                location_name=loc,
                classification="committee-meeting",
            )
            event.dedupe_key = event_name
            event.add_source(url)
            event.add_committee(name)

            if row.xpath('.//a[contains(text(), "View Agenda")]'):
                agenda_url = row.xpath('.//a[contains(text(), "View Agenda")]/@href')[0]
                event.add_document("Agenda", agenda_url, media_type="application/pdf")

            if row.xpath('.//a[contains(text(), "Watch")]'):
                vid_url = row.xpath('.//a[contains(text(), "Watch")]/@href')[0]
                event.add_media_link(
                    "Video of Hearing", vid_url, media_type="text/html"
                )

            if row.xpath('.//tr[contains(@class,"bill-container")]/td'):
                agenda = event.add_agenda_item("Bills under consideration")
                for bill_row in row.xpath('.//tr[contains(@class,"bill-container")]'):
                    bill_id = bill_row.xpath(
                        ".//a[contains(@class,'bill-name-link')]/text()"
                    )[0]
                    agenda.add_bill(bill_id)

            yield event
