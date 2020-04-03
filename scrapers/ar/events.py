import re
import csv
import datetime
from io import StringIO

from openstates_core.scrape import Scraper, Event

import pytz

# ftp://www.arkleg.state.ar.us/dfadooas/ReadMeScheduledMeetings.txt
_TIMECODES = {
    "12:34 PM": "Upon Recess of the House",
    "12:36 PM": "10 Minutes Upon Adjournment of",
    "12:37 PM": "Upon Adjournment of Afternoon Joint Budget Committee",
    "12:38 PM": "15 Minutes Upon Adjournment of Senate",
    "12:39 PM": "15 Minutes Upon Adjournment of House",
    "12:40 PM": "Upon Adjournment of Senate",
    "12:41 PM": "Upon Adjournment of House",
    "12:42 PM": "Upon Adjournment of",
    "12:43 PM": "Upon Adjournment of Both Chambers",
    "12:44 PM": "10 Minutes upon Adjournment",
    "12:46 PM": "Upon Adjournment of House Rules",
    "12:47 PM": "Rescheduled",
    "12:48 PM": "Upon Adjournment of Joint Budget",
    "12:49 PM": "15 Minutes upon Adjournment",
    "12:50 PM": "30 Minutes upon Adjournment",
    "12:51 PM": "1 Hour prior to Senate convening",
    "12:52 PM": "1 Hour prior to House convening",
    "12:53 PM": "30 Minutes prior to Senate convening",
    "12:54 PM": "30 Minutes prior to House convening",
    "12:55 PM": "Meeting Cancelled",
    "12:56 PM": "No Meeting Scheduled",
    "12:57 PM": "Call of Chair",
    "12:58 PM": "To Be Announced",
    "12:59 PM": "Upon Adjournment",
}


class AREventScraper(Scraper):
    _tz = pytz.timezone("America/Chicago")

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        url = "ftp://www.arkleg.state.ar.us/dfadooas/ScheduledMeetings.txt"
        page = self.get(url)
        page = csv.reader(StringIO(page.text), delimiter="|")

        for row in page:
            # Deal with embedded newline characters, which cause fake new rows
            LINE_LENGTH = 11
            while len(row) < LINE_LENGTH:
                row += next(page)

            desc = row[7].strip()

            match = re.match(r"^(.*)- (HOUSE|SENATE)$", desc)
            if match:

                comm = match.group(1).strip()
                comm = re.sub(r"\s+", " ", comm)
                location = row[5].strip() or "Unknown"
                when = datetime.datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
                when = self._tz.localize(when)
                # Only assign events to a session if they are in the same year
                # Given that session metadata have some overlap and
                # missing end dates, this is the best option available
                session_year = int(session[:4])
                if session_year != when.year:
                    continue

                description = "%s MEETING" % comm
                event = Event(
                    name=description,
                    start_date=when,
                    location_name=location,
                    description=description,
                )
                event.add_source(url)

                event.add_participant(comm, type="committee", note="host")
                # time = row[3].strip()
                # if time in _TIMECODES:
                #     event['notes'] = TIMECODES[time]

                yield event
