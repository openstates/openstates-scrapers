import logging
import os
from datetime import date

import dateutil.parser
import pytz
import requests
from openstates.scrape import Scraper, Event
from .utils import add_space

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

    def in_request(self, url):
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
        res = requests.get(url, headers=headers)

        if res.status_code != 200:
            res.raise_for_status()
        return res

    def scrape(self):
        res = self.in_request(f"{self.base_url}/{self.session}/standing-committees")

        for committee in res.json()["items"]:
            committee_path = committee["link"].replace(
                "standing-committees", "committees"
            )
            url = f"{self.base_url}{committee_path}/meetings"
            yield from self.extract_committee_events(url)

    def extract_committee_events(self, url):

        res = self.in_request(url)
        for meeting in res.json()["items"]:
            link = meeting["link"]
            _id = link.split("/")[-1]

            extra_details = self.in_request(f"{self.base_url}{link}").json()

            date = meeting["meetingdate"].replace(" ", "")
            time = meeting["starttime"].replace(" ", "")
            location = meeting["location"] or extra_details["location"] or "See Agenda"
            chamber = (
                meeting["committee"]["chamber"]
                .replace("(S)", "Senate")
                .replace("(H)", "House")
            )
            video_url = f"https://iga.in.gov//legislative/{self.session}/meeting/watchlive/{_id}"

            if extra_details["cancelled"] != "False":
                continue

            try:
                when = dateutil.parser.parse(f"{date} {time}")
            except dateutil.parser.ParserError:
                log.info(f"Could not parse date: {date} {time}")
                when = dateutil.parser.parse(date)
            when = self._tz.localize(when)

            event = Event(
                name=chamber,
                start_date=when,
                location_name=location,
                classification="committee-meeting",
            )
            event.add_source(url)
            event.add_participant(chamber, type="committee", note="host")
            event.add_media_link("Video of Hearing", video_url, media_type="text/html")
            agenda = event.add_agenda_item("Bills under consideration")
            for bill in extra_details["agenda"]:

                if bill.get("bill"):
                    bill_id = bill.get("bill").get("billName")
                    bill_id = add_space(bill_id)
                    agenda.add_bill(bill_id)

            yield event
