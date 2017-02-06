import re

from billy.scrape.committees import CommitteeScraper, Committee


class NHCommitteeScraper(CommitteeScraper):
    jurisdiction = 'nh'
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
        return committee

    def _parse_code(self, code):
        return self._code_pattern.search(code).group()

    def _parse_url(self, code):
        return self._url_map[code[0].lower()].format(code)

    def _parse_chamber(self, code):
        return self._chamber_map[code[0].lower()]

    def scrape(self, chamber, term):
        for committee in self._parse_committees_text(chamber):
            self.save_committee(committee)
