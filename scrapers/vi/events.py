import lxml.html
import re

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape
from ics import Calendar


class VIEventScraper(Scraper):
    def scrape(self):

        url = "https://legvi.org/calendars/"

        page = self.get(url).content
        page = lxml.html.fromstring(page)

        for row in page.xpath("//article[contains(@class,'mec-event-article')]//a[1]"):
            title = row.xpath("text()")[0]
            if "reserved" in title.lower():
                self.info(f"Skipping {title}, reserved.")
                continue

            event_id = row.xpath("@data-event-id")[0]
            yield from self.parse_event(event_id)

        if not page.xpath("//article[contains(@class,'mec-event-article')]"):
            yield EmptyScrape

    def parse_event(self, event_id):
        # https://legvi.org/?method=ical&id=1381956
        url = f"https://legvi.org/?method=ical&id={event_id}"
        ical = self.get(url).text
        cal = Calendar(ical)

        for e in cal.events:
            event = Event(
                e.name,
                str(e.begin),
                e.location,
                description=e.description,
                end_date=str(e.end),
            )
            event.add_participant(e.organizer.common_name, "person")

            if "committee" in e.name.lower():
                com_name = e.name.replace("Committee on", "")
                event.add_participant(com_name, "committee")

            for match in re.findall(r"Bill No\.\s(\d+\-\d+)", e.description):
                event.add_bill(match)

            event.add_source(e.url)

            yield event
