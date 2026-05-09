import datetime
import json

import lxml
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
    events_web_lxml_cache = None

    def __init__(self, *args, **kwargs):
        super(CTEventScraper, self).__init__(*args, **kwargs)

    def scrape(self):
        # Add a committee code in this array to just test a specific code
        only_do_these_codes = []
        for code, name in self.get_comm_codes():
            if len(only_do_these_codes) == 0 or code in only_do_these_codes:
                yield from self.scrape_committee_events(code, name)

    def scrape_committee_events(self, code, name):
        events_url = (
            "http://www.cga.ct.gov/basin/fullcalendar/commevents.php?"
            f"comm_code={code}"
        )
        event_objects = set()
        events_data = self.get(events_url, verify=False).text

        if not events_data:
            self.info(f"No events from {code} from normal source, trying web backup")
            # for some reason not getting this committee from original source
            # try backup web scrape instead
            yield from self.scrape_committee_events_web(name)
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

    def scrape_committee_events_web(self, comm_name):
        """A backup scraping method for when a committee like FIN stops appearing in the original source"""
        if self.events_web_lxml_cache:
            # use the cache so we're not hitting the same request multiple times
            # code could be refactored here, but since this is a backup to the main method, leaving as is for now
            events_html = self.events_web_lxml_cache
        else:
            today = datetime.datetime.today()
            data = {
                "sDate": datetime.datetime(today.year, 1, 1).strftime("%m/%d/%Y"),
                "eDate": today.strftime("%m/%d/%Y"),
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            events_response = self.post(
                "https://www.cga.ct.gov/in-events1x.asp",
                data=data,
                headers=headers,
                verify=False,
            )
            events_html = lxml.html.fromstring(events_response.content)
        event_rows = events_html.xpath("//tbody/tr")
        for row in event_rows:
            cells = row.xpath("td")
            date_str = cells[0].text_content().strip()
            time_str = cells[1].text_content().strip()
            title_link = cells[2].xpath(".//a")
            if len(title_link) == 0:
                # we only consider events that have a link to an event agenda
                continue
            elif len(title_link) > 1:
                raise Exception(
                    f"Unexpected more than one link in event title cell for {date_str} {time_str}"
                )
            event_title = title_link[0].text_content().strip()
            if comm_name.lower() not in event_title.lower():
                # check if the committee name is in this list
                continue
            event_url_partial = title_link[0].get("href")
            event_url = f"https://www.cga.ct.gov{event_url_partial}"
            event_location_str = cells[3].text_content().strip()
            event_datetime = datetime.datetime.strptime(
                f"{date_str} {time_str}", "%m/%d/%Y %I:%M %p"
            )

            event = Event(
                start_date=self._tz.localize(event_datetime),
                location_name=event_location_str,
                name=event_title,
                description=event_title,
            )
            event.add_source("https://www.cga.ct.gov/")
            event.add_committee(comm_name)
            event.add_link(event_url, note="Agenda")
            event.dedupe_key = (
                f"{comm_name}#{event_title}#{event_datetime}#{event_location_str}"
            )

            # agenda handling
            for bill in Agenda(source=URL(event_url, verify=False)).do_scrape():
                event.add_bill(bill)

            yield event

    def get_comm_codes(self):
        url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = self.get(url)
        page = open_csv(page)
        return [(row["comm_code"].strip(), row["comm_name"].strip()) for row in page]
