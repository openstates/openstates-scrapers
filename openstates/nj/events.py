import datetime as dt
from dbfpy import dbf
import pytz
import re
from .utils import DBFMixin

from billy.scrape.events import EventScraper, Event

agenda_dbf = "ftp://www.njleg.state.nj.us/ag/2012data/AGENDAS.DBF"

class NJEventScraper(EventScraper, DBFMixin):
    jurisdiction = 'nj'
    _tz = pytz.timezone('US/Eastern')

    def initialize_committees(self, year_abr):
        chamber = {'A':'Assembly', 'S': 'Senate', '':''}

        com_url, com_db = self.get_dbf(year_abr, 'COMMITT')

        self._committees = {}
        # There are some IDs that are missing. I'm going to add them
        # before we load the DBF, in case they include them, we'll just
        # override with their data.
        #
        # This data is from:
        # http://www.njleg.state.nj.us/media/archive_audio2.asp?KEY=<KEY>&SESSION=2012
        overlay = {
            'A': 'Assembly on the Whole',
            'S': 'Senate on the Whole',
            'J': 'Joint Legislature on the Whole',
            'ABUB': 'Assembly Budget Committee',
            'JBOC': 'Joint Budget Oversight',
            'JPS': 'Joint Committee on the Public Schools',
            'LRC': 'New Jersey Law Revision Commission',
            'PHBC': 'Pension and Health Benefits Review Commission',
            'SBAB': 'Senate Budget and Appropriations Committee',
            'JLSU': 'Space Leasing and Space Utilization Committee',
            'SUTC': 'Sales and Use Tax Review Commission',
            'SPLS': 'Special Session'
        }
        self._committees = overlay

        for com in com_db:
            # map XYZ -> "Assembly/Senate _________ Committee"
            self._committees[com['CODE']] = ' '.join((chamber[com['HOUSE']],
                                                      com['DESCRIPTIO'],
                                                      'Committee'))

    def scrape(self, chamber, session):
        year_abr = ((int(session) - 209) * 2) + 2000
        self.initialize_committees(year_abr)
        url, db = self.get_dbf(year_abr, "AGENDAS")
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
            hr_name = self._committees[record['COMMHOUSE']]

            event = Event(
                session,
                date_time,
                'committee:meeting',
                "Meeting of the %s" % ( hr_name ),
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

            event.add_participant("host",
                                  hr_name,
                                  'committee',
                                  committee_code=record['COMMHOUSE'],
                                  chamber=chamber)
            event.add_source(agenda_dbf)
            self.save_event(event)
