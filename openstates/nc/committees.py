from pupa.scrape import Scraper, Organization

import lxml.html


class NCCommitteeScraper(Scraper):
    def scrape_committee(self, committee, url):
        url = url.replace(" ", "%20") + "&bPrintable=true"
        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        for row in doc.xpath("//table/tr"):
            children = row.getchildren()
            if len(children) != 2:
                self.info("skipping members for " + committee.name)
                continue
            mtype, members = row.getchildren()
            if mtype.text == "Members":
                for m in members.getchildren():
                    member_name = self._clean_member_name(m.text)
                    committee.add_member(member_name)
            else:
                member_name = self._clean_member_name(members.text_content())
                committee.add_member(member_name, mtype.text)

    def _clean_member_name(self, name):
        """Names are displayed as "Office. LastName" (e.g. "Rep. Adams"). This strips the "Office."

        This helps link this to the correct legislator.
        """
        for prefix in ["Rep. ", "Sen. "]:
            if name.startswith(prefix):
                return name.replace(prefix, "")

        # If none hit, return the name as is
        return name

    def scrape(self, chamber=None):
        base_url = (
            "http://www.ncleg.net/gascripts/Committees/"
            "Committees.asp?bPrintable=true&sAction=ViewCommitteeType&sActionDetails="
        )

        chamber_slugs = {
            "upper": ["Senate%20Standing", "Senate%20Select"],
            "lower": ["House%20Standing", "House%20Select"],
        }

        if chamber:
            chambers = [chamber]
        else:
            chambers = ["upper", "lower"]

        for chamber in chambers:
            for ctype in chamber_slugs[chamber]:
                data = self.get(base_url + ctype).text
                doc = lxml.html.fromstring(data)
                doc.make_links_absolute(base_url + ctype)
                for comm in doc.xpath("//ul/li/a"):
                    name = comm.text
                    # skip committee of whole Senate
                    if "Whole Senate" in name:
                        continue
                    url = comm.get("href")
                    committee = Organization(
                        name=name, chamber=chamber, classification="committee"
                    )
                    self.scrape_committee(committee, url)
                    committee.add_source(url)
                    if not committee._related:
                        self.warning("empty committee: %s", name)
                    else:
                        yield committee
