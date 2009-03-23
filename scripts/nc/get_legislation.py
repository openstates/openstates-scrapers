#!/usr/bin/env python

import urllib
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

def clean_legislators(s):
    s = s.replace('&nbsp;', ' ').strip()
    return [l.strip() for l in s.split(';') if l]

class NCLegislationScraper(LegislationScraper):

    state = 'nc'

    def get_bill_info(self, session, bill_id):
        bill_detail_url = 'http://www.ncga.state.nc.us/gascripts/BillLookUp/BillLookUp.pl?Session=%s&BillID=%s' % (session, bill_id)

        # parse the bill data page, finding the latest html text
        bill_data = urllib.urlopen(bill_detail_url).read()
        bill_soup = BeautifulSoup(bill_data)
        links = bill_soup.findAll('a')
        best_url = None
        for link in links:
            if link.has_key('href') and link['href'].startswith('/Sessions'):
                if not best_url or link['href'].endswith('.html'):
                    best_url = link['href']
        best_url = 'http://www.ncga.state.nc.us' + best_url

        if bill_id[0] == 'H':
            chamber = 'lower'
        else:
            chamber = 'upper'

        self.add_bill(chamber, session, bill_id, '-title-fix-me-', best_url)

        # grab primary and cosponsors from table[6]
        tables = bill_soup.findAll('table')
        sponsor_rows = tables[6].findAll('tr')
        sponsors = clean_legislators(sponsor_rows[1].td.contents[0])
        for leg in sponsors:
            self.add_sponsorship(chamber, session, bill_id, 'primary', leg)
        cosponsors = clean_legislators(sponsor_rows[2].td.contents[0])
        for leg in cosponsors:
            self.add_sponsorship(chamber, session, bill_id, 'cosponsor', leg)

        # easier to read actions from the rss.. but perhaps favor less HTTP requests?
        rss_url = 'http://www.ncga.state.nc.us/gascripts/BillLookUp/BillLookUp.pl?Session=%s&BillID=%s&view=history_rss' % (session, bill_id)
        rss_data = urllib.urlopen(rss_url).read()
        rss_soup = BeautifulSoup(rss_data)
        # title looks like 'House Chamber: action'
        for item in rss_soup.findAll('item'):
            action = item.title.contents[0]
            pieces = item.title.contents[0].split(' Chamber: ')
            if len(pieces) == 2:
                action_chamber = pieces[0]
                action = pieces[1]
            else:
                action_chamber = None
                action = pieces[0]
            date = item.pubdate.contents[0]
            self.add_action(chamber, session, bill_id, action_chamber, action, date)

    def scrape_session(self, chamber, session):
        url = 'http://www.ncga.state.nc.us/gascripts/SimpleBillInquiry/displaybills.pl?Session=%s&tab=Chamber&Chamber=%s' % (session, chamber)
        data = urllib.urlopen(url).read()
        print url
        print data
        soup = BeautifulSoup(data)

        rows = soup.findAll('table')[5].findAll('tr')[1:]
        for row in rows:
            td = row.find('td')
            bill_id = td.a.contents[0]
            self.get_bill_info(session, bill_id)

    def scrape_bills(self, chamber, year):
        year_mapping = {
            #'1985': ('1985',),
            #'1986': ('1985E1',),
            #'1987': ('1987',),
            #'1988': (),
            #'1989': ('1989', '1989E1'),
            #'1990': ('1989E2',),
            #'1991': ('1991E1', '1991'),
            #'1992': (),
            #'1993': ('1993',),
            #'1994': ('1993E1',),
            #'1995': ('1995',),
            '1996': ('1995E1', '1995E2'),
            '1997': ('1997',),
            '1998': ('1997E1',),
            '1999': ('1999E1', '1999'),
            '2000': ('1999E2',),
            '2001': ('2001',),
            '2002': ('2001E1',),
            '2003': ('2003', '2002E1', '2003E2'),
            '2004': ('2003E3',),
            '2005': ('2005',),
            '2006': (),
            '2007': ('2007E1', '2007'),
            '2008': ('2007E2',),
            '2009': ('2009',),
        }
        chamber = {'lower':'House', 'upper':'Senate'}[chamber]

        if year not in year_mapping:
            raise NoDataForYear(year)

        for session in year_mapping[year]:
            self.scrape_session(chamber, session)

if __name__ == '__main__':
    NCLegislationScraper().run()
