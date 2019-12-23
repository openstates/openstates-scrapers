import re

from pupa.scrape import Scraper, Organization

import lxml.html

nelis_root = "https://www.leg.state.nv.us/App/NELIS/REL"


class NVCommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber:
            chambers = [chamber]
        else:
            chambers = ["upper", "lower"]
        for chamber in chambers:
            insert = self.jurisdiction.session_slugs[self.latest_session()]

            chamber_names = {"lower": "Assembly", "upper": "Senate"}
            list_url = "%s/%s/HomeCommittee/LoadCommitteeListTab" % (nelis_root, insert)
            html = self.get(list_url).text
            doc = lxml.html.fromstring(html)

            sel = "panel%sCommittees" % chamber_names[chamber]

            ul = doc.xpath('//ul[@id="%s"]' % sel)[0]
            coms = ul.xpath('li/div/div/div[@class="col-md-4"]/a')

            for com in coms:
                name = com.text.strip()
                com_id = re.match(
                    r".*/Committee/(?P<id>[0-9]+)/Overview", com.attrib["href"]
                ).group("id")
                com_url = (
                    "%s/%s/Committee/FillSelectedCommitteeTab?committeeOrSubCommitteeKey=%s"
                    "&selectedTab=Overview" % (nelis_root, insert, com_id)
                )
                org = Organization(
                    name=name, chamber=chamber, classification="committee"
                )
                org.add_source(com_url)
                self.scrape_comm_members(chamber, org, com_url)
                yield org

    def scrape_comm_members(self, chamber, committee, url):

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        links = doc.xpath('//a[@class="bio"]')
        for link in links:
            name = link.text.strip()
            role = link.tail.strip().replace("- ", "")
            if role == "":
                role = "member"
            committee.add_member(name, role=role)
