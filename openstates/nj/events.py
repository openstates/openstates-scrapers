import datetime as dt
import pytz
import re
from .utils import MDBMixin

from billy.scrape.events import EventScraper, Event


class NJEventScraper(EventScraper, MDBMixin):
    jurisdiction = 'nj'
    _tz = pytz.timezone('US/Eastern')

    def initialize_committees(self, year_abr):
        chamber = {'A':'Assembly', 'S': 'Senate', '':''}

        com_csv = self.access_to_csv('Committee')

        self._committees = {}
        
        # There are some IDs that are missing. I'm going to add them
        # before we load the DBF, in case they include them, we'll just
        # override with their data.
        overlay = {
            'A': 'Assembly on the Whole',
            'S': 'Senate on the Whole',
            'J': 'Joint Legislature on the Whole',
            'TED': "First Legislative District Economic Development Task Force",
            'ABUB': 'Assembly Budget Committee',
            'JBOC': 'Joint Budget Oversight',
            'JPS': 'Joint Committee on the Public Schools',
            'LRC': 'New Jersey Law Revision Commission',
            'LSI': 'Select Committee on Investigation',
            'PHBC': 'Pension and Health Benefits Review Commission',
            'SBAB': 'Senate Budget and Appropriations Committee',
            'JLSU': 'Space Leasing and Space Utilization Committee',
            'SUTC': 'Sales and Use Tax Review Commission',
            'SPLS': 'Special Session',
            'JCES': 'Joint Committee on Ethical Standards',
            'JEJ': 'Joint Committee on Economic Justice and Equal Employment Opportunity',
            'LSC': 'Legislative Services Commission',
            'THIE': 'Senate Task Force on Health Insurance Exchange Implementation Committee',
            'CASC': 'College Affordability Study Commission',
            'CIR': 'State Commission of Investigation'
        }
        self._committees = overlay

        for com in com_csv:
            # map XYZ -> "Assembly/Senate _________ Committee"
            self._committees[com['Code']] = ' '.join((chamber[com['House']],
                                                      com['Description'],
                                                      'Committee'))

    def scrape(self, chamber, session):
        year_abr = ((int(session) - 209) * 2) + 2000
        self._init_mdb(year_abr)
        self.initialize_committees(year_abr)
        records = self.access_to_csv("Agendas")
        for record in records:
            if record['Status'] != "Scheduled":
                continue
            description = record['Comments']
            related_bills = []

            for bill in re.findall("(A|S)(-)?(\d{4})", description):
                related_bills.append({
                    "bill_id" : "%s %s" % ( bill[0], bill[2] ),
                    "descr": description
                })

            date_time = "%s %s" % (record['Date'], record['Time'])
            date_time = dt.datetime.strptime(date_time, "%m/%d/%Y %I:%M %p")
            hr_name = self._committees[record['CommHouse']]

            event = Event(
                session,
                date_time,
                'committee:meeting',
                "Meeting of the %s" % ( hr_name ),
                location=record['Location'] or "Statehouse",
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
                }[record['CommHouse'][0].lower()]
            except KeyError:
                chamber = "joint"

            event.add_participant("host",
                                  hr_name,
                                  'committee',
                                  committee_code=record['CommHouse'],
                                  chamber=chamber)
            event.add_source('http://www.njleg.state.nj.us/downloads.asp')
            self.save_event(event)
