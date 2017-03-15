from pupa.scrape import Scraper, Organization
import scrapelib
from openstates.utils import LXMLMixin


class ORCommitteeScraper(Scraper, LXMLMixin):
    def scrape(self, chamber=None):
        chambers = {
            "upper": "SenateCommittees_search",
            "lower": "HouseCommittees_search",
            "joint": "JointCommittees_search"
        }

        page = self.lxmlize(
            "https://olis.leg.state.or.us/liz/Committees/list/"
        )

        for chamber, id_ in chambers.items():
            for committee_entry in page.xpath("//ul[@id='{}']//li/a".format(id_)):
                committee_url = committee_entry.attrib['href']
                try:
                    page = self.lxmlize(committee_url)
                except scrapelib.HTTPError as e:
                    self.warning(e)
                    return None

                committee = Organization(chamber=chamber, name=committee_entry.text,
                                         classification='committee')
                base_url = "https://olis.leg.state.or.us"
                ppl_link = base_url + page.xpath(".//div[@id='Membership']/@data-load-action")[0]
                ppl_page = self.lxmlize(ppl_link)
                people = ppl_page.xpath(".//tr")
                titles = ["Senator ", "Representative ",
                          "President Pro Tempore ",
                          "President ",
                          "Senate Republican Leader ",
                          "Senate Democratic Leader ",
                          "House Democratic Leader ",
                          "House Republican Leader ",
                          "Vice Chair", "Chair", "Speaker "]
                for row in people:
                    role, who = [x.text_content().strip() for x in row.xpath("./td")]
                    for title in titles:
                        who = who.replace(title, " ")
                    who = who.strip().strip(",").strip()
                    who = " ".join(who.split())
                    committee.add_member(who, role=role)
                committee.add_source(committee_url)
                yield committee
