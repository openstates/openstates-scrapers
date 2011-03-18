from billy.scrape.bills import BillScraper, Bill

import scrapelib
import lxml.etree


class NYBillScraper(BillScraper):
    state = 'ny'

    def scrape(self, chamber, session):
        try:
            for index in xrange(1, 1000):
                url = ("http://open.nysenate.gov/legislation/search/"
                       "?search=otype:bill&searchType=&format=xml"
                       "&pageIdx=%d" % index)
                with self.urlopen(url) as page:
                    page = lxml.etree.fromstring(page)

                    for bill in page.xpath("//result[@type = 'bill']"):
                        print bill.attrib['id']
                        id = bill.attrib['id'].split('-')[0]
                        title = bill.attrib['title'].strip()
                        primary_sponsor = bill.attrib['sponsor']

                        if id.startswith('S'):
                            bill_chamber = 'upper'
                        else:
                            bill_chamber = 'lower'

                        if chamber != bill_chamber:
                            continue

                        bill = Bill(session, chamber, id, title)
                        bill.add_source(url)
                        bill.add_sponsor('primary', primary_sponsor)

                        self.save_bill(bill)
        except scrapelib.HTTPError as e:
            if e.response.code != 404:
                raise