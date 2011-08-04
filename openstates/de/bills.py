from billy.scrape.bills import BillScraper, Bill
import lxml.html
import re

class DEBillScraper(BillScraper):
    state = 'de'

    urls = {
        '2011-2012': {
            'lower': (
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=1',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=2',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=3',
                'http://legis.delaware.gov/LIS/lis146.nsf/Legislation?OpenView&Start=1&Count=10000&Expand=4'
            ),
            'upper': (
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

        bill_id = bill['id'].replace('w/','with ')

        page = lxml.html.fromstring(self.urlopen(bill['url']))
        page.make_links_absolute(bill['url'])

        sponsors_row = page.xpath('//tr[td/b[contains(font,"Primary Sponsor")]]')[0]
        sponsor = sponsors_row.xpath('td[@width="31%"]/font')[0].text

        additional = sponsors_row.xpath('td[@width="48%"]/font')
        additional_sponsors = additional[0].text if len(additional) > 0 else ""
        additional_sponsors = additional_sponsors.replace('&nbsp&nbsp&nbsp','')

        cosponsors_row = page.xpath('//tr[td/b[contains(font,"CoSponsors")]]')[0]
        cosponsors = cosponsors_row.xpath('td[@width="79%"]/font')[0].text
        cosponsors = cosponsors if cosponsors != '{ NONE...}' else ''

        title_row = page.xpath('//tr[td/b[contains(font,"Long Title")]]')[0]
        # text_content() == make sure any tags in the title don't cause issues
        title = title_row.xpath('td[@width="79%"]/font')[0].text_content() 

        self.log('Title: ' + title)
        self.log('Sponsor: ' + sponsor)
        self.log('Additional sponsors: ' + additional_sponsors)
        self.log('Co-sponsors: ' + cosponsors)
        self.log('*'*50)

        # Save bill
        b = Bill(bill['session'], bill['chamber'], bill_id, title)
        b.add_source(bill['url'])
        self.save_bill(b)
