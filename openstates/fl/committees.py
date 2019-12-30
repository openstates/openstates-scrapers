from pupa.scrape import Scraper, Organization
from spatula import Spatula, Page
from .utils import fix_name


class HouseComList(Page):
    url = "http://www.myfloridahouse.gov/Sections/Committees/committees.aspx"
    list_xpath = "//a[contains(@href, 'committeesdetail.aspx')]"

    def handle_page(self):
        # don't use handle_page_item because we need to look back at prior element
        parent = None

        for item in self.doc.xpath(self.list_xpath):
            cssclass = item.attrib.get("class", "")
            name = item.text_content().strip()

            if "parentcommittee" in cssclass:
                parent = None
                chamber = "lower"

            comm = Organization(
                name=name, classification="committee", chamber=chamber, parent_id=parent
            )
            yield self.scrape_page(HouseComDetail, item.attrib["href"], obj=comm)

            # parent for next time
            if "parentcommittee" in cssclass:
                parent = comm._id
                chamber = None


class HouseComDetail(Page):
    def clean_name(self, name):
        name = name.replace(" [D]", "")
        name = name.replace(" [R]", "")
        name = name.replace(" [I]", "")
        name = name.strip()
        name = fix_name(name)
        return name

    def handle_page(self):
        name = self.doc.xpath('//h1[@class="cd_ribbon"]')[0].text

        for lm in self.doc.xpath('//div[@class="cd_LeaderMember"]'):
            role = lm.xpath('.//div[@class="cd_LeaderTitle"]')[0].text_content().strip()
            name = (
                lm.xpath('.//span[@class="cd_LeaderTitle"]/a')[0].text_content().strip()
            )
            name = self.clean_name(name)
            self.obj.add_member(name, role=role)

        for cm in self.doc.xpath('//p[@class="cd_committeemembers"]//a'):
            name = self.clean_name(cm.text_content())
            self.obj.add_member(name)

        self.obj.add_source(self.url)

        yield self.obj


class SenComList(Page):
    url = "http://www.flsenate.gov/Committees/"
    list_xpath = "//a[contains(@href, 'Committees/Show')]/@href"

    def handle_list_item(self, item):
        return self.scrape_page(SenComDetail, item)


class SenComDetail(Page):
    def clean_name(self, member):
        member = member.replace("Senator ", "").strip()
        member = member.replace(" (D)", "")
        member = member.replace(" (R)", "")
        member = member.replace(" (I)", "")
        member = fix_name(member)
        return member

    def handle_page(self):
        name = self.doc.xpath('//h2[@class="committeeName"]')[0].text
        if name.startswith("Appropriations Subcommittee"):
            return
            # TODO: restore scraping of Appropriations Subcommittees
            # name = name.replace('Appropriations ', '')
            # parent = {'name': 'Appropriations', 'classification': 'upper'}
            # chamber = None
        else:
            if name.startswith("Committee on"):
                name = name.replace("Committee on ", "")
            parent = None
            chamber = "upper"
        comm = Organization(
            name=name, classification="committee", chamber=chamber, parent_id=parent
        )

        for dt in self.doc.xpath('//div[@id="members"]/dl/dt'):
            role = dt.text.replace(": ", "").strip().lower()
            member = dt.xpath("./following-sibling::dd")[0].text_content()
            member = self.clean_name(member)
            comm.add_member(member, role=role)

        for ul in self.doc.xpath('//div[@id="members"]/ul/li'):
            member = self.clean_name(ul.text_content())
            comm.add_member(member)

        comm.add_source(self.url)

        yield comm


class FlCommitteeScraper(Scraper, Spatula):
    def scrape(self):
        yield from self.scrape_page_items(SenComList)
        yield from self.scrape_page_items(HouseComList)
