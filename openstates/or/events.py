import datetime
import re
import logging
import pprint
import pytz

from pupa.scrape import Scraper, Event
from .apiclient import OregonLegislatorODataClient
from .utils import SESSION_KEYS, index_legislators

logger = logging.getLogger("openstates")


class OREventScraper(Scraper):
    _TZ = pytz.timezone("US/Pacific")
    _DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

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
           committees_by_code[committee['CommitteeCode']] = committee["CommitteeName"]

        meetings_response = self.api_client.get(
            "committee_meetings",
            start_date='2020-01-01T08:00:00',
            session='2020R1',
        )

        for meeting in meetings_response:
            event_date = self._TZ.localize(
                datetime.datetime.strptime(
                    meeting['MeetingDate'], self._DATE_FORMAT
                )
            )
            com_name = committees_by_code[meeting['CommitteeCode']]

#         event = Event(start_date=start_date, name=name, location_name=location)

            event = Event(
                start_date = event_date,
                name=com_name,
                location_name=meeting['Location']
            )

            event.add_source("http://w3.akleg.gov/index.php#tab4")

            event.add_participant(com_name, type="committee", note="host")
            yield event
            
        pprint.pprint(meetings_response)

        # measures_response = self.api_client.get(
        #     "measures", page=500, session=session_key
        # )

        # pprint.pprint(response)
        yield {}
