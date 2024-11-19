import re
import pytz
import dateutil
import lxml
from utils.events import match_coordinates
from collections.abc import Generator
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


class MIEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")
    current_page = None

    def scrape(self):
        url = "https://legislature.mi.gov/Committees/Meetings?sortBy=Calendar"
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        if not page.xpath(
            "//table[contains(@class,'calendar')]//a[contains(@href,'/Committees/Meeting')]/@href"
        ):
            raise EmptyScrape

        for link in page.xpath(
            "//table[contains(@class,'calendar')]//a[contains(@href,'/Committees/Meeting')]/@href"
        ):
            yield from self.scrape_event_page(link)

    def scrape_event_page(self, url) -> Generator[Event]:
        status = "tentative"

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        self.current_page = page

        title = self.table_cell("Committee(s)")

        chair = self.table_cell("Chair")

        if "sen." in chair.lower():
            chamber = "Senate"
        elif "rep." in chair.lower():
            chamber = "House"

        where = self.table_cell("Location")

        date = self.table_cell("Date")
        time = self.table_cell("Time")

        if "cancelled" in date.lower():
            status = "cancelled"
            date = date.replace("Cancelled", "")

        if "cancelled" in time.lower():
            status = "cancelled"
            time = time.replace("Cancelled", "")

        when = dateutil.parser.parse(f"{date} {time}")
        when = self._tz.localize(when)

        event = Event(
            name=title,
            start_date=when,
            location_name=where,
            status=status,
        )
        event.add_source(url)

        for com in title.split("joint meeting with"):
            event.add_participant(f"{chamber} {com.strip()}", "organization")

        agenda = self.table_cell("Agenda")

        event.add_agenda_item(agenda)

        matches = re.findall(r"([HRSB]{2}\s\d+)", agenda)
        for match in matches:
            event.add_bill(match)

        match_coordinates(
            event,
            {
                "Binsfeld Office Building": ("42.73204", "-84.55507"),
                "House Office Building": ("42.73444", "-84.55348"),
                "Capitol Building": ("42.73360", "-84.5554"),
            },
        )

        event.dedupe_key = f"{chamber}#{title}#{where}#{when}#{status}"
        yield event

    def table_cell(self, header: str):
        xpath = f"//div[@class='formLeft' and contains(text(),'{header}')]/following-sibling::div[@class='formRight']"
        return self.current_page.xpath(f"string({xpath})").strip()
