import re
import csv
import urllib2

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator


class CTLegislatorScraper(LegislatorScraper):
    state = 'ct'
    latest_only = True

    _committee_names = {}

    def __init__(self, *args, **kwargs):
        super(CTLegislatorScraper, self).__init__(*args, **kwargs)
        self._scrape_committee_names()

    def scrape(self, chamber, term):

        office_code = {'upper': 'S', 'lower': 'H'}[chamber]

        leg_url = "ftp://ftp.cga.ct.gov/pub/data/LegislatorDatabase.csv"
        page = urllib2.urlopen(leg_url)
        page = csv.DictReader(page)

        for row in page:
            if office_code != row['office code']:
                continue

            district = row['dist'].lstrip('0')

            name = row['first name']
            mid = row['middle initial'].strip()
            if mid:
                name += " %s" % mid
            name += " %s" % row['last name']
            suffix = row['suffix'].strip()
            if suffix:
                name += " %s" % suffix

            party = row['party']
            if party == 'Democrat':
                party = 'Democratic'

            office_address = "%s, Room %s\nHartford, CT 06106-1591" % (
                row['capitol street address'], row['room number'])

            leg = Legislator(term, chamber, district,
                             name, first_name=row['first name'],
                             last_name=row['last name'],
                             middle_name=row['middle initial'],
                             suffixes=row['suffix'],
                             party=party,
                             email=row['email'],
                             url=row['URL'],
                             office_address=office_address,
                             office_phone=row['capitol phone'])
            leg.add_source(leg_url)

            for comm_code in row['committee codes'].split(';'):
                if comm_code:
                    comm_name = self._committee_names[comm_code]
                    leg.add_role('committee member', term,
                                 chamber='joint',
                                 committee=comm_name)

            self.save_legislator(leg)

    def _scrape_committee_names(self):
        comm_url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = urllib2.urlopen(comm_url)
        page = csv.DictReader(page)

        for row in page:
            comm_code = row['comm_code'].strip()
            comm_name = row['comm_name'].strip()
            comm_name = re.sub(r' Committee$', '', comm_name)
            self._committee_names[comm_code] = comm_name
