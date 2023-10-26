from openstates.scrape import Scraper, Event
from ics import Calendar
import re
import requests


class GUEventScraper(Scraper):
    short_types = {
        "bill": "B",
        "resolution": "R",
    }

    def scrape(self):
        ical_url = "https://calendar.google.com/calendar/ical/webmaster%40guamlegislature.com/public/basic.ics"

        ical = requests.get(ical_url).text
        self.info("Parsing event feed. This may take a moment.")
        cal = Calendar(ical)
        for e in cal.events:
            location = e.location
            if not location or str(location).strip() == "":
                location = "See Agenda"

            name = e.name
            if not name:
                name = "See Agenda"

            event = Event(
                name,
                str(e.begin),
                location,
                description=str(e.description),
                end_date=str(e.end),
            )

            search_text = f"{e.description} {e.name}"

            bills = set()
            for match in re.findall(
                r"(Bill|Resolution) No\.\s+(\d+\-\d+)", search_text
            ):
                short_type = self.short_types[match[0].lower()]
                bill_id = f"{short_type} {match[1]}"
                bills.add(bill_id)

            for bill in bills:
                event.add_bill(bill)

            for match in re.findall(
                r"(https:\/\/[w\.]*(youtube\.com|youtu\.be)\/[\w\?\=\/]+)",
                str(e.description),
                flags=re.IGNORECASE,
            ):
                match = match[0]
                # manual fix for common bad url
                if match[-7:] == ".com/c/":
                    continue
                event.add_media_link(
                    "Youtube", match, "text/html", on_duplicate="ignore"
                )

            event.add_source(
                "https://guamlegislature.com/index/schedules-and-calendars/"
            )
            yield event
