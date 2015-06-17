from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import scrapelib
from openstates.utils import LXMLMixin


class ORCommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = 'or'

    def scrape(self, term, chambers):
        cdict = {"upper": "SenateCommittees_search",
                 "lower": "HouseCommittees_search",
                 "joint": "JointCommittees_search",}

        slug = self.metadata['session_details'][{
            x['name']: x for x in self.metadata['terms']
        }[term]['sessions'][-1]]['slug']

        page = self.lxmlize(
            "https://olis.leg.state.or.us/liz/%s/Committees/list/" % (
                slug
            )
        )
        for chamber, id_ in cdict.items():
            for committee in page.xpath("//ul[@id='%s']//li/a" % (id_)):
                self.scrape_committee(committee.attrib['href'],
                                      committee.text, chamber)

    def scrape_committee(self, committee_url, committee_name, chamber):
        try:
            page = self.lxmlize(committee_url)
        except scrapelib.HTTPError as e:
            self.warning(e)
            return None
        
        c = Committee(chamber=chamber, committee=committee_name)
        base_url = "https://olis.leg.state.or.us"
        people_link = base_url+page.xpath(".//div[@id='Membership']/@data-load-action")[0]
        people_page = self.lxmlize(people_link)
        people = people_page.xpath(".//tr")
        titles = ["Senator ","Representative ",
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
                who = who.replace(title," ")
            who = who.strip().strip(",").strip()
            who = " ".join(who.split())
            c.add_member(who, role=role)
        c.add_source(committee_url)
        self.save_committee(c)
