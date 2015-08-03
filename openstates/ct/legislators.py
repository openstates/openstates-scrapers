import re
import chardet
import unicodecsv
import StringIO

from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import open_csv


HEADERS = [
    'dist',
    'office code',
    'district number',
    'designator code',
    'first name',
    'middle initial',
    'last name',
    'suffix',
    'commonly used name',
    'home street address',
    'home city',
    'home state',
    'home zip code',
    'home phone',
    'capitol street address',
    'capitol city',
    'capitol phone',
    'room',
    'room number',
    'committees chaired',
    'committees vice chaired',
    'ranking member',
    'committee member1',
    'senator/representative',
    'party',
    'title',
    'gender',
    'business phone',
    'email',
    'fax',
    'prison',
    'URL',
    'committee codes',
]


class CTLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ct'
    latest_only = True

    _committee_names = {}

    def scrape(self, term, chambers):
        leg_url = "ftp://ftp.cga.ct.gov/pub/data/LegislatorDatabase.csv"
        page = self.get(leg_url)

        # Ensure that the spreadsheet's structure hasn't generally changed
        _row_headers = page.text.split('\r\n')[0].replace('"', '').split(',')
        assert _row_headers == HEADERS, "Spreadsheet structure may have changed"

        page = open_csv(page)
        for row in page:

            chamber = {'H': 'lower', 'S': 'upper'}[row['office code']]

            district = row['dist'].lstrip('0')
            assert district.isdigit(), "Invalid district found: {}".format(district)

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
            email = row['email'].strip()
            if "@" not in email:
                assert email.endswith("mailform.php"), "Problematic email found: {}".format(email)
                email = None
            leg.add_office('capitol', 'Capitol Office',
                           address=office_address,
                           phone=row['capitol phone'],
                           fax=(row['fax'].strip() or None),
                           email=email)

            home_address = "{}\n{}, {} {}".format(
                row['home street address'],
                row['home city'],
                row['home state'],
                row['home zip code'],
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
