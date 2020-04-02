import re

import lxml.html
from openstates_core.scrape import Scraper, Organization

from . import utils


class CommitteeDict(dict):
    def __missing__(self, key):
        (chamber, committee_name) = key
        committee = Organization(
            name=committee_name, chamber=chamber, classification="committee"
        )
        self[key] = committee
        return committee


class PACommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        url = utils.urls["committees"][chamber]

        page = self.get(url).text
        page = lxml.html.fromstring(page)

        committees = CommitteeDict()

        for div in page.xpath("//div[@class='MemberInfoCteeList-Member']"):
            _thumbnail, bio, committee_list, _ = list(div)
            name = bio.xpath(".//a")[-1].text_content().strip()
            namey_bits = name.split()
            namey_bits.pop().strip("()")
            name = " ".join(namey_bits).replace(" ,", ",")
            name = " ".join(name.split(", ")[::-1])

            for li in committee_list.xpath("div/ul/li"):

                # Add the ex-officio members to all committees, apparently.
                msg = "Member ex-officio of all Standing Committees"
                if li.text_content() == msg:
                    for (_chamber, _), committee in committees.items():
                        if chamber != _chamber:
                            continue
                        committee.add_member(name, "member")
                    continue

                # Everybody else normal.
                committee_name = li.xpath("a/text()").pop()
                role = "member"
                for _role in li.xpath("i/text()") or []:
                    role = re.sub(r"[\s,]+", " ", _role).lower().strip()

                # Add the committee member.
                key = (chamber, committee_name)
                committees[key].add_member(name, role)

        # Save the non-empty committees.
        for committee in committees.values():
            if not committee._related:
                continue
            committee.add_source(url)
            yield committee
