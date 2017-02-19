from pupa.scrape import Scraper, Organization
from .base import Spatula, Page


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
        #yield from self.scrape_page_items(RepList)
