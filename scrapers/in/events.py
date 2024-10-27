import json
import logging
from datetime import date
from urllib.parse import urljoin

import dateutil.parser
import pytz
from openstates.scrape import Scraper, Event
from .apiclient import ApiClient
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
    base_url = "https://beta-api.iga.in.gov"
    session = date.today().year

    def __init__(self, *args, **kwargs):
        self.apiclient = ApiClient(self)
        super().__init__(*args, **kwargs)

    def scrape(self):
        response = self.apiclient.get("meetings", session=self.session)
        meetings = response["meetings"]
        if len(meetings["items"]) == 0:
            raise EmptyScrape

        for item in meetings["items"]:
            meeting = self.apiclient.get(
                "meeting", session=self.session, meeting_link=item["link"]
            )

            if meeting["cancelled"] != "False":
                continue

            committee = meeting["committee"]

            link = urljoin(self.base_url, meeting["link"])
            _id = link.split("/")[-1]

            date = meeting["meetingdate"].replace(" ", "")
            time = meeting["starttime"]
            if time:
                time = time.replace(" ", "")
                when = dateutil.parser.parse(f"{date} {time}")
                all_day = False
            else:
                when = dateutil.parser.parse(date).date()
                all_day = True
            when = self._tz.localize(when)

            location = meeting["location"] or "See Agenda"

            video_url = (
                f"https://iga.in.gov/legislative/{self.session}/meeting/watchlive/{_id}"
            )

            event_name = f"{committee['chamber']}#{committee['name']}#{location}#{when}"

            event = Event(
                name=committee["name"],
                start_date=when,
                all_day=all_day,
                location_name=location,
                classification="committee-meeting",
            )
            event.dedupe_key = event_name
            event.add_source(link, note="API details")
            name_slug = committee["name"].lower().replace(" ", "-")
            event.add_source(
                f"https://iga.in.gov/{self.session}/committees/{committee['chamber'].lower()}/{name_slug}",
                note="Committee Schedule",
            )
            event.add_participant(committee["name"], type="committee", note="host")
            event.add_media_link("Video of Hearing", video_url, media_type="text/html")
            agenda = event.add_agenda_item("Bills under consideration")

            agendas = meeting.get("agenda")
            if type(agendas) == str:
                agendas = json.loads(meeting.get("agenda"))

            for agenda_item in agendas:
                if not agenda_item.get("bill", None):
                    continue
                bill_id = agenda_item["bill"].get("billName")
                bill_id = add_space(bill_id)
                agenda.add_bill(bill_id)

            yield event
