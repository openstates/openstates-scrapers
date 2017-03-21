from pupa.scrape import Scraper, Organization
from .apiclient import OregonLegislatorODataClient
import scrapelib
from openstates.utils import LXMLMixin


class ORCommitteeScraper(Scraper, LXMLMixin):
    def latest_session(self):
        self.session = self.api_client.get('sessions')[-1]['SessionKey']

    def scrape(self, chamber=None, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        if not session:
            self.latest_session()

        yield from self.scrape_committee()

    def scrape_committee(self):
        committees_response = self.api_client.get('committees', session=self.session)

        #TODO: continue to create committees

    def old_committee_scraper(self):
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
