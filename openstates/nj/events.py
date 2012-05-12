import datetime as dt
from dbfpy import dbf
import pytz
import re

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
            description = record['COMMENTS']
            related_bills = []

            for bill in re.findall("(A|S)(-)?(\d{4})", description):
                related_bills.append({
                    "bill_id" : "%s %s" % ( bill[0], bill[2] ),
                    "descr": description
                })

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
            for bill in related_bills:
                event.add_related_bill(bill['bill_id'],
                                      description=bill['descr'],
                                      type='consideration')
            try:
                chamber = {
                    "a" : "lower",
                    "s" : "upper",
                    "j" : "joint"
                }[record['COMMHOUSE'][0].lower()]
            except KeyError:
                chamber = "joint"

            event.add_participant("host", record['COMMHOUSE'],
                                  chamber=chamber)
            event.add_source(agenda_dbf)
            self.save_event(event)
