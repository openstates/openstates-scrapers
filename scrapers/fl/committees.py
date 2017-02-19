from pupa.scrape import Scraper, Organization, Person
from .base import Spatula, Page

class HouseComList(Page):
    url = "http://www.myfloridahouse.gov/Sections/Committees/committees.aspx"
    list_xpath = "//a[contains(@href, 'committeesdetail.aspx')]/@href"

    def handle_list_item(self, item):
        return self.scrape_page(HouseComDetail, item)


class HouseComDetail(Page):
    def clean_name(self, name):
        name = name.replace(' [D]', '')
        name = name.replace(' [R]', '')
        name = name.replace(' [I]', '')
        return name

    def handle_page(self):
        name = self.doc.xpath('//h1[@class="cd_ribbon"]')[0].text
        comm = Organization(name=name, classification="committee", chamber="lower")

        for lm in self.doc.xpath('//div[@class="cd_LeaderMember"]'):
            role = lm.xpath('.//div[@class="cd_LeaderTitle"]')[0].text_content().strip()
            name = lm.xpath('.//span[@class="cd_LeaderTitle"]/a')[0].text_content().strip()
            name = self.clean_name(name)
            comm.add_member(name, role=role)

        for cm in self.doc.xpath('//p[@class="cd_committeemembers"]//a'):
            name = self.clean_name(cm.text_content())
            comm.add_member(name)

        comm.add_source(self.url)

        yield comm

class SenComList(Page):
    url = "http://www.flsenate.gov/Committees/"
    list_xpath = "//a[contains(@href, 'Committees/Show')]/@href"

    def handle_list_item(self, item):
        return self.scrape_page(SenComDetail, item)


class SenComDetail(Page):
    def clean_name(self, member):
        member = member.replace('Senator ', '')
        member = member.replace(' (D)', '')
        member = member.replace(' (R)', '')
        member = member.replace(' (I)', '')
        return member

    def handle_page(self):
        name = self.doc.xpath('//h2[@class="committeeName"]')[0].text
        comm = Organization(name=name, classification="committee", chamber="upper")

        for dt in self.doc.xpath('//div[@id="members"]/dl/dt'):
            role = dt.text.replace(': ', '').strip().lower()
            member = dt.xpath('./following-sibling::dd')[0].text_content()
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
