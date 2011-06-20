import re

from billy.scrape.bills import BillScraper, Bill

import lxml.html


class WVBillScraper(BillScraper):
    state = 'wv'

    def scrape(self, chamber, session):
        if chamber == 'lower':
            orig = 'h'
        else:
            orig = 's'

        url = ("http://www.legis.state.wv.us/Bill_Status/"
               "Bills_all_bills.cfm?year=%s&sessiontype=RS"
               "&btype=bill&orig=%s" % (session, orig))
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Bills_history')]"):
            bill_id = link.xpath("string()").strip()
            title = link.xpath("string(../../td[2])").strip()
            self.scrape_bill(session, chamber, bill_id, title,
                             link.attrib['href'])

    def scrape_bill(self, session, chamber, bill_id, title, url):
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(url)

        for link in page.xpath("//a[contains(@href, 'bills_text')]"):
            name = link.xpath("string()").strip()
            if name in ['html', 'wpd']:
                continue
            print name
            bill.add_version(name, link.attrib['href'])

        self.save_bill(bill)
