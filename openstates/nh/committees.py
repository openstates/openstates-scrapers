import re

from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin

from openstates.nh import legacy_committees


class NHCommitteeScraper(CommitteeScraper, LXMLMixin):

    terms: [
        {'name': '2011-2012', 'sessions': ['2011', '2012'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014', 'sessions': ['2013', '2014'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016', 'sessions': ['2015', '2016'],
         'start_year': 2015, 'end_year': 2016},
        {'name': '2017-2018', 'sessions': ['2017'],
         'start_year': 2017, 'end_year': 2018}
    ]
    committees_url = 'http://gencourt.state.nh.us/dynamicdatafiles/Committees.txt'

    _code_pattern = re.compile(r'[A-Z][0-9]{2}')
    _chamber_map = {
        's': 'upper',
        'h': 'lower',
    }
    _url_map = {
        's': 'http://www.gencourt.state.nh.us/Senate/'
             'committees/committee_details.aspx?cc={}',
        'h': 'http://www.gencourt.state.nh.us/house/'
             'committees/committeedetails.aspx?code={}',
    }
    _role_map = {
        'chairman': 'chair',
        'v chairman': 'vice chair',
    }

    def _parse_committees_text(self, chamber):
        lines = self.get(self.committees_url).text.splitlines()
        rows = [line.split('|') for line in lines]
        committees = [self._parse_row(row) for row in rows]
        return [
            committee for committee in committees
            if committee and committee['chamber'] == chamber
        ]

    def _parse_row(self, row):
        code, name, _ = row
        # Handle empty code
        if not code:
            return None
        code = self._parse_code(code)
        url = self._parse_url(code)
        chamber = self._parse_chamber(code)
        committee = Committee(chamber, name)
        committee.add_source(url)
        if chamber == 'lower':
            self._parse_members_house(committee, url)
        else:
            self._parse_members_senate(committee, url)
        return committee

    def _parse_code(self, code):
        return self._code_pattern.search(code).group()

    def _parse_url(self, code):
        return self._url_map[code[0].lower()].format(code)

    def _parse_chamber(self, code):
        return self._chamber_map[code[0].lower()]

    def _parse_members_house(self, committee, url):
        page = self.lxmlize(url)
        links = page.xpath('//a[contains(@href, "members/member")]')
        for link in links:
            name = re.sub(r'\s+', ' ', link.text_content()).replace(u'\xa0', ' ').strip()
            role = 'member'
            # Check whether member has a non-default role
            for ancestor in link.iterancestors():
                if ancestor.tag == 'table':
                    if ancestor.attrib.get('id') == 'Table2':
                        header = link.getparent().getprevious()
                        role = header.text_content().strip(':').lower()
                    break
            committee.add_member(name, self._parse_role(role))

    def _parse_members_senate(self, committee, url):
        page = self.lxmlize(url)
        links = page.xpath('//a[contains(@href, "members/webpages")]')
        names = [link.text_content().strip() for link in links]
        if not names:
            return
        # Get intermingled list of members and roles
        rows = [
            each.strip()
            for each in links[0].getparent().text_content().strip().split('\r\n')
            if each.strip()
        ]
        while rows:
            name = rows.pop(0).replace(u'\xa0', ' ')
            role = 'member'
            if rows and rows[0] not in names:
                role = rows.pop(0).lower()
            committee.add_member(name, self._parse_role(role))

    def _parse_role(self, role):
        key = role.lower().replace('.', '')
        return self._role_map.get(key, 'member')

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        years = [int(year) for year in term.split('-')]
        if years[0] < 2017:
            return legacy_committees.NHCommitteeScraper(
                self.metadata,
                self.output_dir,
                self.strict_validation,
            ).scrape(chamber, term)
        for committee in self._parse_committees_text(chamber):
            self.save_committee(committee)
