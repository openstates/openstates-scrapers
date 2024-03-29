import datetime
import json

from openstates.scrape import Scraper, Event

import pytz

from .utils import open_csv


from spatula import PdfPage, URL
import re

# Events before the session year will be skipped
SESSION_YEAR = 2023


bill_re = re.compile(r"(SJ|HJ|HB|HR|SB|SR)\s{0,10}0*(\d+)")


class Agenda(PdfPage):
    def process_page(self):
        # Bills are in the format "S.B. No. 123", this preprocessing step
        # removes a lot of the complexity so the regex can be simpler. After the
        # preprocessing step, the bills should be in the format "SB   123"
        self.text = self.text.upper().replace(".", "").replace("NO", "")

        bills = bill_re.findall(self.text)

        # Format bills with correct spacing and remove duplicates
        formatted_bills = set()
        for alpha, num in bills:
            formatted_bills.add(f"{alpha} {num}")

        yield from formatted_bills


class CTEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    def __init__(self, *args, **kwargs):
        super(CTEventScraper, self).__init__(*args, **kwargs)

    def scrape(self):
        for code, name in self.get_comm_codes():
            yield from self.scrape_committee_events(code, name)

    def scrape_committee_events(self, code, name):
        events_url = (
            "http://www.cga.ct.gov/basin/fullcalendar/commevents.php?"
            f"comm_code={code}"
        )
        event_objects = set()
        events_data = self.get(events_url, verify=False).text

        if not events_data:
            self.info(f"No events from {code}")
            return
        events = json.loads(events_data)

        DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
        for info in events:
            if not info["title"]:
                self.warning("Event found with no title; it will be skipped")
                continue
            elif info["title"].startswith("CANCELLED:"):
                self.info(
                    "Cancelled event found; it will be skipped: {}".format(
                        info["title"]
                    )
                )
                continue
            when = datetime.datetime.strptime(info["start"], DATETIME_FORMAT)

            # Check to make sure event is for current session
            if when.year < SESSION_YEAR:
                continue

            event_name = f"{name}#{info['title']}#{when}"
            if event_name in event_objects:
                self.warning(f"Found duplicate event: {event_name}. Skipping")
                continue
            event_objects.add(event_name)
            # end = datetime.datetime.strptime(info['end'], DATETIME_FORMAT)
            where = "{0} {1}".format(info["building"].strip(), info["location"].strip())
            # end_time=self._tz.localize(end),
            event = Event(
                start_date=self._tz.localize(when),
                location_name=where,
                name=info["title"],
                description=info["title"],
            )
            event.add_source(events_url)
            event.add_committee(name)
            event.dedupe_key = event_name

            # Check for agenda pdf, if it exists then scrape all bill ids from it
            agenda_url = info["url"]
            if agenda_url:
                full_url = f"https://www.cga.ct.gov{agenda_url}"
                for bill in Agenda(source=URL(full_url, verify=False)).do_scrape():
                    event.add_bill(bill)

            yield event

    def get_comm_codes(self):
        url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = self.get(url)
        page = open_csv(page)
        return [(row["comm_code"].strip(), row["comm_name"].strip()) for row in page]
