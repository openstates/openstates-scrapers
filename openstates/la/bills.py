from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill

import lxml.html


URL = "http://www.legis.la.gov/Legis/BillSearchListQ.aspx?r=%s1*"

bill_types = {
    "upper": ["SB", "SCR"],
    "lower": ["HB", "HCR"]
}


class LABillScraper(BillScraper):
    jurisdiction = 'la'

    def lxmlize(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def do_post_back(self, page, event_target, event_argument):
        form = page.xpath("//form[@id='aspnetForm']")[0]
        block = {name: value for name, value in [(obj.name, obj.value)
                    for obj in form.xpath(".//input")]}
        block['__EVENTTARGET'] = event_target
        block['__EVENTARGUMENT'] = event_argument
        ret = lxml.html.fromstring(self.urlopen(form.action,
                                   method=form.method,
                                   body=block))
        ret.make_links_absolute(form.action)
        return ret

    def bill_pages(self, bill_type):
        page = self.lxmlize(URL % (bill_type))
        yield page

        while True:
            hrefs = page.xpath("//a[text()=' > ']")
            if hrefs == [] or "disabled" in hrefs[0].attrib:
                return

            page = self.do_post_back(
                page,
                "ctl00$ctl00$PageBody$PageContent$DataPager1$ctl02$ctl00",
                ""
            )
            yield page


    def scrape(self, chamber, session):
        for bill_type in bill_types[chamber]:
            for bill_page in self.bill_pages(bill_type):
                for bill in bill_page.xpath(
                        "//a[contains(@href, 'BillInfo.aspx')]"):
                    self.scrape_bill_page(chamber, bill.attrib['href'])


    def get_one_xpath(self, page, xpath):
        ret = page.xpath(xpath)
        if len(ret) != 1:
            raise Exception
        return ret[0]


    def scrape_bill_page(self, chamber, bill_url):
        page = self.lxmlize(bill_url)
        author = self.get_one_xpath(
            page,
            "//a[@id='ctl00_PageBody_LinkAuthor']/text()"
        )
        print author
