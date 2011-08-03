from billy.scrape.bills import BillScraper, Bill
import lxml.html
import re

class DEBillScraper(BillScraper):
    state = 'de'

    urls = {
        '2011-2012': {
            'upper': (
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=1',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=2',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=3',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=4'
            ),
            'lower': (
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=5',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=6',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=7',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=8'
            )
        }
    }

    def scrape(self, chamber, session):
        urls = self.urls[session][chamber]
        bills_to_scrape = []

        # gather bills to scrape
        for u in urls:
            page = lxml.html.fromstring(self.urlopen(u))
            page.make_links_absolute(u)
            rows = page.xpath('//tr[td/font/a[contains(@href, "/LIS")]]')
            for r in rows:
                link = r.xpath('td/font/a')[0]
                bills_to_scrape.append({ 
                    'id': link.text,
                    'url': link.attrib['href'],
                    'session': session,
                    'chamber': chamber
                })

        for bill in bills_to_scrape:
            self.scrape_bill(bill)

    def scrape_bill(self, bill):
        self.log(bill['id'])
        self.log(bill['url'])

        page = lxml.html.fromstring(self.urlopen(bill['url']))
        page.make_links_absolute(bill['url'])

        # scrape away ...
        #b = Bill(bill['session'], bill['chamber'], bill['id'], ...)
        #self.save_bill(b)
