import re
import csv
import datetime
import cStringIO as StringIO

from billy.scrape.events import EventScraper, Event


# ftp://www.arkleg.state.ar.us/dfadooas/ReadMeScheduledMeetings.txt
TIMECODES = {
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


class AREventScraper(EventScraper):
    jurisdiction = 'ar'

    def scrape(self, session, chambers):
        url = "ftp://www.arkleg.state.ar.us/dfadooas/ScheduledMeetings.txt"
        page = self.get(url)
        page = csv.reader(StringIO.StringIO(page.content), delimiter='|')

        for row in page:
            # Deal with embedded newline characters, which cause fake new rows
            LINE_LENGTH = 11
            while len(row) < LINE_LENGTH:
                row += page.next()
                assert (len(row) <= LINE_LENGTH,
                        "Line is too long: {}".format(row))

            desc = row[7].strip()

            match = re.match(r'^(.*)- (HOUSE|SENATE)$', desc)
            if match:
                comm_chamber = {'HOUSE': 'lower',
                                'SENATE': 'upper'}[match.group(2)]

                comm = match.group(1).strip()
                comm = re.sub(r'\s+', ' ', comm)
                location = row[5].strip() or 'Unknown'
                when = datetime.datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S')

                # Only assign events to a session if they are in the same year
                # Given that session metadata have some overlap and
                # missing end dates, this is the best option available
                session_year = int(session[:4])
                if session_year != when.year:
                    continue

                event = Event(session, when, 'committee:meeting',
                              "%s MEETING" % comm,
                              location=location)
                event.add_source(url)

                event.add_participant('host', comm, 'committee',
                                      chamber=comm_chamber)

                time = row[3].strip()
                if time in TIMECODES:
                    event['notes'] = TIMECODES[time]

                self.save_event(event)
