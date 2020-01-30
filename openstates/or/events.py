import datetime
import logging
import pytz

from pupa.scrape import Scraper, Event
from .apiclient import OregonLegislatorODataClient
from .utils import SESSION_KEYS

logger = logging.getLogger("openstates")


class OREventScraper(Scraper):
    _TZ = pytz.timezone("US/Pacific")
    _DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
    _SOURCE_BASE = "https://olis.oregonlegislature.gov/liz/{}/Committees/{}/{}/Agenda"

    def scrape(self, session=None, window=None):
        self.api_client = OregonLegislatorODataClient(self)
        if not session:
            session = self.latest_session()
        yield from self.scrape_events(session)

    def scrape_events(self, session):
        session_key = SESSION_KEYS[session]

        committees_by_code = {}

        committees_response = self.api_client.get("committees", session=session_key)
        for committee in committees_response:
            committees_by_code[committee["CommitteeCode"]] = committee["CommitteeName"]

        meetings_response = self.api_client.get(
            "committee_meetings", start_date="2020-01-01T08:00:00", session=session_key,
        )

        for meeting in meetings_response:
            event_date = self._TZ.localize(
                datetime.datetime.strptime(meeting["MeetingDate"], self._DATE_FORMAT)
            )
            com_name = committees_by_code[meeting["CommitteeCode"]]

            event = Event(
                start_date=event_date, name=com_name, location_name=meeting["Location"]
            )

            event.add_source(meeting["AgendaUrl"])

            event.extras["meeting_guid"] = meeting["MeetingGuid"]

            event.add_participant(com_name, type="committee", note="host")

            for row in meeting["CommitteeAgendaItems"]:
                if row["Comments"] is not None:
                    agenda = event.add_agenda_item(row["Comments"])

                if row["MeasureNumber"] is not None:
                    bill_id = "{} {}".format(row["MeasurePrefix"], row["MeasureNumber"])
                    agenda.add_bill(bill_id)

            for row in meeting["CommitteeMeetingDocuments"]:
                event.add_document(
                    note=row["ExhibitTitle"],
                    url=row["DocumentUrl"],
                    on_duplicate="ignore",
                )
            yield event
