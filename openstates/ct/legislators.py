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
    '_?',
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
    '_capitol city state zip',
    'capitol phone',
    '_room',
    'room number',
    '_chair of',
    '_vice chair of',
    '_ranking member of',
    'committee member1',
    'title',
    'party',
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

            # Ensure that the spreadsheet's structure hasn't generally changed
            if (row['_blank'] != ' ' or
                    row['_zero'] != '0' or
                    not row['_capitol city state zip'].startswith("Hartford, CT")):
                self.warning(row)
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

            leg = Legislator(term, chamber, district, name,
                             party=party,
                             url=row['URL'])

            office_address = "%s\nRoom %s\nHartford, CT 06106" % (
                row['capitol street address'], row['room number'])
            leg.add_office('capitol', 'Capitol Office',
                           address=office_address,
                           phone=row['capitol phone'],
                           email=row['email'])

            home_address = "{}\n{}, {} {}".format(
                row['home street address'],
                row['home city'],
                row['home state'],
                row['home zip'],
            )
            if "Legislative Office Building" not in home_address:
                leg.add_office('district', 'District Office',
                               address=home_address,
                               phone=row['home phone'] if row['home phone'].strip() else None)

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

                    leg.add_role(role, term,
                                 chamber='joint',
                                 committee=comm)

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
