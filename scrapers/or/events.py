import datetime
import logging
import pytz

from openstates.scrape import Scraper, Event
from .apiclient import OregonLegislatorODataClient
from .utils import SESSION_KEYS

logger = logging.getLogger("openstates")


class OREventScraper(Scraper):
    _TZ = pytz.timezone("US/Pacific")
    _DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
    _SOURCE_BASE = "https://olis.oregonlegislature.gov/liz/{}/Committees/{}/{}/Agenda"

    # this scraper supports a start_date argument of Y-m-d
    # ex: pupa update or events --scrape start_date=2020-01-01
    # if you choose a start date in a previous session, make sure to also pass the relevant session
    # due to API limitations, each scrape will only scrape the events in that provided (or current) session
    def scrape(self, session=None, start_date=None):
        self.api_client = OregonLegislatorODataClient(self)
        if not session:
            session = self.latest_session()
        yield from self.scrape_events(session, start_date)

    def scrape_events(self, session, start_date):
        session_key = SESSION_KEYS[session]

        if start_date is None:
            start_date = datetime.date.today()
        else:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')

        committees_by_code = {}

        committees_response = self.api_client.get("committees", session=session_key)
        for committee in committees_response:
            committees_by_code[committee["CommitteeCode"]] = committee["CommitteeName"]

        meetings_response = self.api_client.get(
            "committee_meetings",
            start_date=start_date.strftime(self._DATE_FORMAT),
            session=session_key,
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
            event.extras["committee_code"] = committee["CommitteeCode"]

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
