from utils import LXMLMixin
from openstates.scrape import Scraper, Organization

COMMITTEE_URL = "http://leg.colorado.gov/content/committees"


class COCommitteeScraper(Scraper, LXMLMixin):
    def scrape_page(self, link, chamber=None):
        page = self.lxmlize(link.attrib["href"])
        comName = link.text
        roles = {
            "Chair": "chair",
            "Vice Chair": "vice-chair",
            "Vice-Chair": "vice-chair",
        }
        committee = Organization(comName, chamber=chamber, classification="committee")
        committee.add_source(link.attrib["href"])

        for member in page.xpath(
            '//div[@class="members"]/' + 'div[@class="roster-item"]'
        ):
            details = member.xpath('.//div[@class="member-details"]')[0]
            person = details.xpath("./h4")[0].text_content()
            # This page does random weird things with whitepace to names
            person = " ".join(person.strip().split())
            if not person:
                continue
            role = details.xpath('./span[@class="member-role"]')
            if role:
                role = roles[role[0].text]
            else:
                role = "member"
            committee.add_member(person, role=role)
        yield committee

    def scrape(self, chambers=None):
        page = self.lxmlize(COMMITTEE_URL)
        # Actual class names have jquery uuids in them, so use
        # contains as a workaround
        comList = page.xpath("//div[contains(@class," + '"view-committees-overview")]')
        seen = set()

        for comType in comList:
            try:
                header = comType.xpath('./div[@class="view-header"]/h3/text()')[0]
            except IndexError:
                self.warning("Blank committees list found.")
                break
            if "House Committees" in header:
                chamber = "lower"
            elif "Senate Committees" in header:
                chamber = "upper"
            else:
                chamber = "legislature"
            for comm in comType.xpath(
                './div[@class="view-content"]' + "/table/tbody/tr/td"
            ):
                link = comm.xpath(".//a")
                # ignore empty cells
                if link:
                    link = link[0]
                    if link.text in seen:
                        continue
                    else:
                        seen.add(link.text)
                    yield from self.scrape_page(link, chamber)
