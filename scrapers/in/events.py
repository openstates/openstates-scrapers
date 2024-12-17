import json
import re
from datetime import date
from urllib.parse import urljoin

import dateutil.parser
import pytz
from openstates.scrape import Scraper, Event
from .apiclient import ApiClient
from .utils import add_space, backoff
from openstates.exceptions import EmptyScrape


class INEventScraper(Scraper):
    _tz = pytz.timezone("America/Indianapolis")
    base_url = "https://api.iga.in.gov"
    session = date.today().year

    def __init__(self, *args, **kwargs):
        self.apiclient = ApiClient(self)
        super().__init__(*args, **kwargs)

    def scrape(self):
        session_no = backoff(self.apiclient.get_session_no, self.session)
        response = self.apiclient.get("meetings", session=self.session)

        meetings = response["meetings"]
        if not meetings["items"]:
            raise EmptyScrape("No meetings found in the response.")

        for item in meetings["items"]:
            meeting = self.apiclient.get(
                "meeting", session=self.session, meeting_link=item["link"]
            )

            if meeting["cancelled"] != "False":
                continue

            committee = meeting["committee"]
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

            link = urljoin(self.base_url, meeting["link"])
            _id = link.split("/")[-1]

            date_str = meeting["meetingdate"].replace(" ", "")
            time_str = meeting["starttime"]
            custom_start_string = ""
            # Determine the 'when' variable based on the presence of time
            if time_str:
                time_str = time_str.replace(
                    " ", ""
                )  # Clean up any spaces in the time string
                when = dateutil.parser.parse(f"{date_str} {time_str}")
                when = self._tz.localize(when)
                all_day = False
            else:
                when = dateutil.parser.parse(date_str).date()
                all_day = True
                if "customstart" in meeting and meeting["customstart"] != "":
                    custom_start_string = f" - {meeting['customstart']}"

            location = meeting["location"] or "See Agenda"
            video_url = (
                f"https://iga.in.gov/legislative/{self.session}/meeting/watchlive/{_id}"
            )

            event = Event(
                name=f"{committee_name}{custom_start_string}",
                start_date=when,
                all_day=all_day,
                location_name=location,
                classification="committee-meeting",
            )
            event.dedupe_key = meeting["link"]
            event.add_source(link, note="API details")
            name_slug = re.sub("[^a-zA-Z0-9]+", "-", committee_name.lower())

            document_url = f"https://iga.in.gov/pdf-documents/{session_no}/{self.session}/{committee_chamber}/committees/{committee_type}/{name_slug}/{_id}/meeting.pdf"

            event.add_source(
                f"https://iga.in.gov/{self.session}/committees/{committee['chamber'].lower() or 'interim'}/{name_slug}",
                note="Committee Schedule",
            )
            event.add_participant(committee_name, type="committee", note="host")
            event.add_document(
                "Meeting Agenda", document_url, media_type="application/pdf"
            )
            event.add_media_link("Video of Hearing", video_url, media_type="text/html")

            agendas = meeting["agenda"]
            if isinstance(agendas, str):
                agendas = json.loads(agendas)
            agenda = event.add_agenda_item("Bills under consideration")
            for agenda_item in agendas:
                if agenda_item.get("bill", None):
                    bill_id = agenda_item["bill"].get("billName")
                    bill_id = add_space(bill_id)
                    agenda.add_bill(bill_id)
                else:
                    agenda.add_subject(agenda_item["description"])

            for exhibit in meeting.get("exhibits"):
                exhibit_pdf_url = self.apiclient.get_document_url(
                    exhibit["pdfDownloadLink"]
                )
                if exhibit_pdf_url:
                    event.add_document(
                        exhibit["description"],
                        exhibit_pdf_url,
                        media_type="application/pdf",
                    )

            for minute in meeting.get("minutes"):
                if minute["link"]:
                    minute_pdf_url = f"https://iga.in.gov/pdf-documents/{session_no}/{self.session}/{committee_chamber}/committees/{committee_type}/{name_slug}/{_id}/{_id}_minutes.pdf"
                    event.add_document(
                        "Meeting Minutes",
                        minute_pdf_url,
                        media_type="application/pdf",
                    )

            yield event
