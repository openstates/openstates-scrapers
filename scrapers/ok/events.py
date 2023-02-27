import re
import json
import dateutil.parser
import pytz

# import lxml.html
import requests
import datetime
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

# from utils.events import match_coordinates


class OKEventScraper(Scraper):
    _tz = pytz.timezone("CST6CDT")
    session = requests.Session()

    def scrape(self, chamber=None):

        start = datetime.datetime(2023, 2, 1).isoformat()
        end = datetime.datetime(2023, 2, 28).isoformat()

        yield from self.scrape_page(start, end)

    def scrape_page(self, start, end, offset=0, limit=20):
        url = "https://www.okhouse.gov/api/events"

        post_data = {
            "start": "2023-02-01T05:00:00.000Z",
            "end": "2023-04-01T03:59:59.999Z",
            "offset": offset,
            "limit": limit,
        }

        headers = {"origin": "https://www.okhouse.gov", "user-agent": "openstates.org"}

        page = requests.post(
            url=url, data=json.dumps(post_data), headers=headers, allow_redirects=True
        ).content
        page = json.loads(page)

        print(page)

        if len(page["events"]["data"]) == 0:
            raise EmptyScrape

        for row in page["events"]["data"]:
            meta = row["attributes"]

            status = "tentative"

            if meta["isCancelled"] is True:
                status = "cancelled"

            location = meta["location"]
            if re.match(r"^room [\w\d]+$", location, flags=re.I) or re.match(
                r"senate room [\w\d]+$", location, flags=re.I
            ):
                location = f"{location} 2300 N Lincoln Blvd, Oklahoma City, OK 73105"

            when = dateutil.parser.parse(meta["startDatetime"])
            # when = self._tz.localize(when)

            event = Event(
                name=meta["title"],
                location_name=location,
                start_date=when,
                classification="committee-meeting",
                status=status,
            )
            event.dedupe_key = f"ok-{meta['slug']}"
            event.add_source("https://ok.gov")
            yield event

        # for row in page.xpath('//tr[contains(@id,"_dgrdNotices_")]'):

        #     if re.match(r"^room [\w\d]+$", location, flags=re.I) or re.match(
        #         r"senate room [\w\d]+$", location, flags=re.I
        #     ):
        #         location = f"{location} 2300 N Lincoln Blvd, Oklahoma City, OK 73105"

        #     event = Event(
        #         name=title,
        #         location_name=location,
        #         start_date=when,
        #         classification="committee-meeting",
        #         status=status,
        #     )
        #     event.dedupe_key = event_name
        #     event.add_source(url)

        #     event.add_committee(title, note="host")

        #     event.add_document("Agenda", agenda_url, media_type="application/pdf")

        #     match_coordinates(event, {"2300 N Lincoln Blvd": (35.49293, -97.50311)})

        #     event_count += 1
        #     yield event

        # if event_count < 1:
        #     raise EmptyScrape
