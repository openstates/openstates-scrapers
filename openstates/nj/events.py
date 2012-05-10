import datetime as dt
import pytz
from dbfpy import dbf

from billy.scrape.events import EventScraper, Event

agenda_dbf = "ftp://www.njleg.state.nj.us/ag/2012data/AGENDAS.DBF"

class NJEventScraper(EventScraper):
    state = 'nj'
    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        name, resp = self.urlretrieve(agenda_dbf)
        db = dbf.Dbf(name)
        records = [ x.asDict() for x in db ]
        for record in records:
            if record['STATUS'] != "Scheduled":
                continue
            print record
            date_time = "%s %s" % (
                record['DATE'],
                record['TIME']
            )
            date_time = dt.datetime.strptime(date_time, "%m/%d/%Y %I:%M %p")
            event = Event(
                session,
                date_time,
                'committee:meeting',
                record['COMMENTS'] or "Meeting Notice",
                location=record['LOCATION'] or "Statehouse",
            )
            event.add_participant("host", record['COMMHOUSE'])
            event.add_source(agenda_dbf)
            self.save_event(event)
