import re
import csv
import datetime

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event


class AREventScraper(EventScraper):
    state = 'ar'

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)
        if chamber == 'other':
            return

        url = "ftp://www.arkleg.state.ar.us/dfadooas/ScheduledMeetings.txt"
        page = self.urlopen(url)
        page = csv.reader(StringIO.StringIO(page), delimiter='|')

        seen = set()

        for row in page:
            desc = row[7].strip()

            match = re.match(r'^(.*)- (HOUSE|SENATE)$', desc)
            if match:
                comm_chamber = {'HOUSE': 'lower',
                                'SENATE': 'upper'}[match.group(2)]
                if comm_chamber != chamber:
                    continue

                comm = match.group(1).strip()
                comm = re.sub(r'\s+', ' ', comm)

                location = row[5].strip() or 'Unknown'

                when = datetime.datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S')
                event = Event(session, when, 'committee:meeting',
                              "%s MEETING" % comm,
                              location=location)
                event.add_source(url)

                self.save_event(event)
