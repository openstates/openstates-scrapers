from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html


class ORCommitteeScraper(CommitteeScraper):
    jurisdiction = 'or'

    def lxmlize(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape(self, term, chambers):
        cdict = {"upper": "SenateCommittees_search",
                 "lower": "HouseCommittees_search",
                 "joint": "JointCommittees_search",}

        page = self.lxmlize("https://olis.leg.state.or.us/liz/Committees/list/")
        for chamber, id_ in cdict.items():
            for committee in page.xpath("//ul[@id='%s']//li/a" % (id_)):
                self.scrape_committee(committee.attrib['href'],
                                      committee.text, chamber)

    def scrape_committee(self, committee_url, committee_name, chamber):
        page = self.lxmlize(committee_url)
        people = page.xpath("//div[@id='membership']//tbody/tr")
        c = Committee(chamber=chamber, committee=committee_name)
        for row in people:
            role, who = [x.text_content().strip() for x in row.xpath("./td")]
            c.add_member(who, role=role)
        c.add_source(committee_url)
        self.save_committee(c)
