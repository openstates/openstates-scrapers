import re
import chardet
import unicodecsv
import StringIO

from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import open_csv


HEADERS = [
    'dist',
    'office code',
    '_dist',
    'party',
    'first name',
    'middle initial',
    'last name',
    'suffix',
    '_first name',
    'home street address',
    'home city',
    'home state',
    'home zip',
    'home phone',
    'capitol street address',
    '_capitol city state',
    'capitol phone',
    '_room',
    'room number',
    '_chair of',
    '_vice chair of',
    '_ranking member of',
    'committee member1',
    'title',
    '_party',
    '_role',
    '_gender',
    '_extra phone',
    'email',
    '_blank',
    '_zero',
    'URL',
    '_committee codes',
]


class CTLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ct'
    latest_only = True

    _committee_names = {}

    def scrape(self, term, chambers):
        leg_url = "ftp://ftp.cga.ct.gov/pub/data/LegislatorDatabase.csv"
        data = self.get(leg_url)
        char_encoding = chardet.detect(data.content)['encoding']
        page = unicodecsv.reader(
            StringIO.StringIO(data.content),
            delimiter=',',
            encoding=char_encoding
        )

        for row in page:
            row = dict(zip(HEADERS, row))

            if row['_blank'] != ' ' or row['_zero'] != '0':
                raise AssertionError("Spreadsheet structure may have changed")

            chamber = {'H': 'lower', 'S': 'upper'}[row['office code']]

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

            leg = Legislator(term, chamber, district,
                             name, first_name=row['first name'],
                             last_name=row['last name'],
                             middle_name=row['middle initial'],
                             suffixes=row['suffix'],
                             party=party,
                             email=row['email'].strip(),
                             url=row['URL'],
                             office_phone=row['capitol phone'])

            office_address = "%s, Room %s\nHartford, CT 06106-1591" % (
                row['capitol street address'], row['room number'])
            leg.add_office('capitol', 'Capitol Office',
                           address=office_address, phone=row['capitol phone'])
            # skipping home address for now
            leg.add_source(leg_url)

            for comm in row['committee member1'].split(';'):
                if comm:
                    if ' (' in comm:
                        comm, role = comm.split(' (')
                        role = role.strip(')').lower()
                    else:
                        role = 'member'
                    comm = comm.strip()
                    if comm == '':
                        continue

                    leg.add_role('committee member', term,
                                 chamber='joint',
                                 committee=comm,
                                 position=role)

            self.save_legislator(leg)

    def _scrape_committee_names(self):
        comm_url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = self.get(comm_url)
        page = open_csv(page)

        for row in page:
            comm_code = row['comm_code'].strip()
            comm_name = row['comm_name'].strip()
            comm_name = re.sub(r' Committee$', '', comm_name)
            self._committee_names[comm_code] = comm_name
