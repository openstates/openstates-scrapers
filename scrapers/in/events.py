import json
import logging
import re
from datetime import date
from urllib.parse import urljoin

import dateutil.parser
import pytz
from openstates.scrape import Scraper, Event
from .apiclient import ApiClient
from .utils import add_space
from openstates.exceptions import EmptyScrape


log = logging.getLogger(__name__)
PROXY_BASE_URL = "https://in-proxy.openstates.org/"


class INEventScraper(Scraper):
    _tz = pytz.timezone("America/Indianapolis")
    base_url = "https://beta-api.iga.in.gov"
    session = date.today().year

    def __init__(self, *args, **kwargs):
        self.apiclient = ApiClient(self)
        super().__init__(*args, **kwargs)

    def scrape(self):
        session_no = self.apiclient.get_session_no(self.session)
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
            committee_name = (
                committee["name"]
                .replace(",", "")
                .replace("Committee on", "Committee")
                .strip()
            )
            committee_type = (
                "conference"
                if "Conference" in committee["name"]
                else ("standing" if committee["chamber"] else "interim")
            )
            committee_chamber = (
                committee["chamber"].lower() if committee["chamber"] else "universal"
            )
            date = meeting["meetingdate"].replace(" ", "")
            time = meeting["starttime"]
            if time:
                time = time.replace(" ", "")
                when = dateutil.parser.parse(f"{date} {time}")
                when = self._tz.localize(when)
                all_day = False
            else:
                when = dateutil.parser.parse(date).date()
                all_day = True

            location = meeting["location"] or "See Agenda"

            video_url = (
                f"https://iga.in.gov/legislative/{self.session}/meeting/watchlive/{_id}"
            )
            event_name = f"{committee['chamber']}#{committee_name}#{location}#{when}"

            event = Event(
                name=committee_name,
                start_date=when,
                all_day=all_day,
                location_name=location,
                classification="committee-meeting",
            )
            event.dedupe_key = event_name
            event.add_source(link, note="API details")
            name_slug = committee_name.lower().replace(" ", "-")
            name_slug = re.sub("[^a-zA-Z0-9]+", "-", committee_name.lower())

            document_url = f"https://iga.in.gov/pdf-documents/{session_no}/{self.session}/{committee_chamber}/committees/{committee_type}/{name_slug}/{_id}/meeting.pdf"

            event.add_source(
                f"https://iga.in.gov/{self.session}/committees/{committee['chamber'].lower() or 'interim'}/{name_slug}",
                note="Committee Schedule",
            )
            event.add_participant(committee_name, type="committee", note="host")
            event.add_document(
                "Meeting Agenda", document_url, media_type="applicaiton/pdf"
            )
            event.add_media_link("Video of Hearing", video_url, media_type="text/html")

            agendas = meeting["agenda"]
            if type(agendas) is str:
                agendas = json.loads(meeting["agenda"])
            if agendas:
                agenda = event.add_agenda_item("Bills under consideration")

            for agenda_item in agendas:
                if agenda_item.get("bill", None):
                    bill_id = agenda_item["bill"].get("billName")
                    bill_id = add_space(bill_id)
                    agenda.add_bill(bill_id)
                else:
                    agenda.add_subject(agenda_item["description"])

            for exhibit in meeting.get("exhibits"):
                # Original URL
                # exhibit_pdf_url = self.apiclient.get_document_url(
                #     exhibit["pdfDownloadLink"]
                # )
                # Proxy URL
                exhibit_pdf_url = urljoin(PROXY_BASE_URL, exhibit["pdfDownloadLink"])
                self.logger.info(exhibit_pdf_url)
                if exhibit_pdf_url:
                    event.add_document(
                        exhibit["description"],
                        exhibit_pdf_url,
                        media_type="application/pdf",
                    )

            for minute in meeting.get("minutes"):
                if minute["link"]:
                    # Original URL
                    # minute_pdf_url = f"https://iga.in.gov/pdf-documents/{session_no}/{self.session}/{committee_chamber}/committees/{committee_type}/{name_slug}/{_id}/{_id}_minutes.pdf"
                    # Proxy URL
                    minute_pdf_url = urljoin(PROXY_BASE_URL, minute["link"])
                    event.add_document(
                        "Meeting Minutes",
                        minute_pdf_url,
                        media_type="application/pdf",
                    )

            yield event
