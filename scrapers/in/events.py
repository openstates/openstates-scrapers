import logging
import os
from datetime import date

import dateutil.parser
from http import HTTPStatus
import pytz
import requests
import time
from openstates.scrape import Scraper, Event
from .utils import add_space
from openstates.exceptions import EmptyScrape


log = logging.getLogger(__name__)


class INEventScraper(Scraper):
    _tz = pytz.timezone("America/Indianapolis")
    # avoid cloudflare blocks for no UA
    cf_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/108.0.0.0 Safari/537.36"  # noqa
    }
    base_url = "https://api.iga.in.gov"
    session = date.today().year
    _session = requests.Session()
    _retry_codes = (
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    )

    def _in_request(self, url):
        """
        Make request to INDIANA API
        """
        apikey = os.environ["INDIANA_API_KEY"]
        useragent = os.getenv("USER_AGENT", self.cf_headers["User-Agent"])
        headers = {
            "Authorization": apikey,
            "Accept": "application/json",
            "User-Agent": useragent,
        }
        res = self._session.get(url, headers=headers)
        attempts = 0
        while attempts < 5 and res.status_code in self._retry_codes:
            log.warning(
                f"Got rate-limiting error response {res.status_code} for {url}. Retrying..."
            )
            attempts += 1
            time.sleep(15)
            res = self._session.get(url, headers=headers)
        if res.status_code == 520:
            self.logger.warning(f"Got CloudFlare error for {url}. Skipping...")
            return {}
        res.raise_for_status()
        return res

    def scrape(self):
        res = self._in_request(f"{self.base_url}/{self.session}/standing-committees")
        if not res:
            raise EmptyScrape

        for committee in res.json()["items"]:
            committee_path = committee["link"].replace(
                "standing-committees", "committees"
            )
            url = f"{self.base_url}{committee_path}/meetings"
            for event in self.extract_committee_events(url, committee):
                yield event

    def extract_committee_events(self, url, committee):

        res = self._in_request(url)
        if not res:
            return []
        event_names = set()
        committee_name = f"{committee['chamber']} {committee['name']}"
        for meeting in res.json()["items"]:
            if meeting["cancelled"] != "False":
                continue

            link = meeting["link"]
            _id = link.split("/")[-1]
            extra_details = self._in_request(f"{self.base_url}{link}").json()

            date = meeting["meetingdate"].replace(" ", "")
            time = meeting["starttime"]
            if time:
                time = time.replace(" ", "")
            location = (
                meeting["location"]
                or extra_details.get("location", None)
                or "See Agenda"
            )
            video_url = (
                f"https://iga.in.gov/legislative/{self.session}/meeting/watchlive/{_id}"
            )

            try:
                when = dateutil.parser.parse(f"{date} {time}")
            except dateutil.parser.ParserError:
                log.info(f"Could not parse date: {date} {time}")
                when = dateutil.parser.parse(date)
            when = self._tz.localize(when)
            event_name = f"{committee['chamber']}#{committee['name']}#{location}#{when}"
            if event_name in event_names:
                self.warning(f"Duplicate event {event_name}")
                continue
            event_names.add(event_name)
            event = Event(
                name=committee_name,
                start_date=when,
                location_name=location,
                classification="committee-meeting",
            )
            event.dedupe_key = event_name
            event.add_source(url, note="API document")
            event.add_source(f"{self.base_url}{link}", note="API details")
            name_slug = committee["name"].lower().replace(" ", "-")
            event.add_source(
                f"https://iga.in.gov/{self.session}/committees/{committee['chamber'].lower()}/{name_slug}",
                note="Committee Schedule",
            )
            event.add_participant(committee_name, type="committee", note="host")
            event.add_media_link("Video of Hearing", video_url, media_type="text/html")
            agenda = event.add_agenda_item("Bills under consideration")
            for item in extra_details.get("agenda", []):
                if not item.get("bill", None):
                    continue
                bill_id = item["bill"].get("billName")
                bill_id = add_space(bill_id)
                agenda.add_bill(bill_id)
            yield event
