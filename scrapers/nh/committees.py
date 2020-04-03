import re

from openstates_core.scrape import Scraper, Organization
from openstates.utils import LXMLMixin


class NHCommitteeScraper(Scraper, LXMLMixin):

    committees_url = "http://gencourt.state.nh.us/dynamicdatafiles/Committees.txt"

    _code_pattern = re.compile(r"[A-Z][0-9]{2}")
    _chamber_map = {"s": "upper", "h": "lower"}
    _url_map = {
        "s": "http://www.gencourt.state.nh.us/Senate/"
        "committees/committee_details.aspx?cc={}",
        "h": "http://www.gencourt.state.nh.us/house/"
        "committees/committeedetails.aspx?code={}",
    }
    _role_map = {"chairman": "chair", "v chairman": "vice chair"}

    def _parse_committees_text(self, chamber):
        lines = self.get(self.committees_url).text.splitlines()
        rows = [line.split("|") for line in lines]
        committees = {}
        for row in rows:
            try:
                committee, com_chamber = self._parse_row(row)
                committees[committee] = com_chamber
            except TypeError:
                self.warning("Skipping Bad Row")
        return [
            committee
            for committee, com_chamber in committees.items()
            if committee and com_chamber == chamber
        ]

    def _parse_row(self, row):
        code, name, _ = row
        # Handle empty code
        if not code:
            return None
        code = self._parse_code(code)
        url = self._parse_url(code)
        chamber = self._parse_chamber(code)
        committee = Organization(chamber=chamber, name=name, classification="committee")
        committee.add_source(url)
        if chamber == "lower":
            self._parse_members_house(committee, url)
        else:
            self._parse_members_senate(committee, url)
        return committee, chamber

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
            name = (
                re.sub(r"\s+", " ", link.text_content()).replace(u"\xa0", " ").strip()
            )
            role = "member"
            # Check whether member has a non-default role
            for ancestor in link.iterancestors():
                if ancestor.tag == "table":
                    if ancestor.attrib.get("id") == "Table2":
                        header = link.getparent().getprevious()
                        role = header.text_content().strip(":").lower()
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
            for each in links[0].getparent().text_content().strip().split("\r\n")
            if each.strip()
        ]
        while rows:
            name = rows.pop(0).replace(u"\xa0", " ")
            role = "member"
            if rows and rows[0] not in names:
                role = rows.pop(0).lower()
            committee.add_member(name, self._parse_role(role))

    def _parse_role(self, role):
        key = role.lower().replace(".", "")
        return self._role_map.get(key, "member")

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            for committee in self._parse_committees_text(chamber):
                yield committee
