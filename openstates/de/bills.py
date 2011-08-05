from billy.scrape.bills import BillScraper, Bill
from datetime import datetime
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

    vote_urls = {}


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

        for bill_id, votes in self.vote_urls.iteritems():
            for url in votes['urls']:
                self.scrape_votes(bill_id, url)
        
        self.vote_urls = {}


    def scrape_bill(self, bill):
        self.log(bill['id'])
        self.log(bill['url'])

        bill_id = bill['id'].replace('w/','with ')

        page = lxml.html.fromstring(self.urlopen(bill['url']))
        page.make_links_absolute(bill['url'])

        title_row = page.xpath('//tr[td/b[contains(font,"Long Title")]]')[0]
        # text_content() == make sure any tags in the title don't cause issues
        title = title_row.xpath('td[@width="79%"]/font')[0].text_content() 

        # now we can create a bill object
        b = Bill(bill['session'], bill['chamber'], bill_id, title)
        b.add_source(bill['url'])

        sponsors_row = page.xpath('//tr[td/b[contains(font,"Primary Sponsor")]]')[0]
        sponsor = sponsors_row.xpath('td[@width="31%"]/font')[0].text
        b.add_sponsor('primary', sponsor)

        # scraping these and co-sponsors, but not doing anything with them until 
        # it's decided whether or not to attempt to split 'em up
        additional = sponsors_row.xpath('td[@width="48%"]/font')
        additional_sponsors = additional[0].text if len(additional) > 0 else ""
        additional_sponsors = additional_sponsors.replace('&nbsp&nbsp&nbsp','')

        cosponsors_row = page.xpath('//tr[td/b[contains(font,"CoSponsors")]]')[0]
        cosponsors = cosponsors_row.xpath('td[@width="79%"]/font')[0].text
        cosponsors = cosponsors if cosponsors != '{ NONE...}' else ''

        introduced_row = page.xpath('//tr[td/b[contains(font,"Introduced On")]]')
        if len(introduced_row) > 0:
            introduced = introduced_row[0].expath('/td[@width="31%"]/font')[0].text
            introduced = datetime.strptime(introduced, '%b %d, %Y')
            b.add_action(bill['chamber'], 'introduced', introduced, 'bill:introduced')

        actions = page.xpath('//table[preceding-sibling::b[contains(font,"Actions History:")]]/tr/td[@width="79%"]/font')
        if len(actions) > 0:
           actions = actions[0].text_content().split('\n') 
           for act in actions:
               act = act.partition(' - ')
               date = datetime.strptime(act[0], '%b %d, %Y')
               b.add_action(bill['chamber'], act[2], date)
        

        # resources = page.xpath('//tr[td/b[contains(font, "Full text of Legislation")]]')

        # save vote urls for scraping later
        voting_reports = page.xpath('//tr[td/b[contains(font, "Voting Reports")]]')
        if(len(voting_reports) > 0):
            for report in voting_reports[0].xpath('td/font/a'):
                if self.vote_urls.has_key(bill_id):
                    self.vote_urls[bill_id]['urls'].append(report.attrib['href'])
                else:
                    self.vote_urls[bill_id] = { 'urls': [report.attrib['href']] }
        
        
        self.log('Title: ' + title)
        self.log('Sponsor: ' + sponsor)
        self.log('Additional sponsors: ' + additional_sponsors)
        self.log('Co-sponsors: ' + cosponsors)
        self.log('*'*50)

        # Save bill
        self.save_bill(b)
    

    def scrape_votes(self, bill_id, url):
        self.log(bill_id)
        self.log(url)
        self.log('*'*50)
