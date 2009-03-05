#!/usr/bin/env python

import urllib
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import run_legislation_scraper

def scrape_session(chamber, session):
    url = 'http://www.ncga.state.nc.us/gascripts/SimpleBillInquiry/displaybills.pl?Session=%s&tab=Chamber&Chamber=%s' % (session, chamber)
    data = urllib.urlopen(url).read()
    soup = BeautifulSoup(data)

    rows = soup.findAll('table')[5].findAll('tr')[1:]
    for row in rows:
        td = row.find('td')
        bill_id = td.a.contents[0]
        bill_detail_url = 'http://www.ncga.state.nc.us%s' % td.a['href']

        # parse the bill data page, finding the latest html text
        bill_data = urllib.urlopen(bill_detail_url).read()
        bill_soup = BeautifulSoup(bill_data)
        links = bill_soup.findAll('a')
        best_url = None
        for link in links:
            if link.has_key('href') and link['href'].startswith('/Sessions'):
                if not best_url or link['href'].endswith('.html'):
                    best_url = link['href']
        yield {'state':'NC', 'chamber':chamber, 'session':session,
               'bill_id':bill_id, 'remote_url':best_url}

def scrape_legislation(chamber, year):
    year_mapping = {
        '1985': ('1985',),
        '1986': ('1985E1',),
        '1987': ('1987',),
        '1988': (),
        '1989': ('1989', '1989E1'),
        '1990': ('1989E2',),
        '1991': ('1991E1', '1991'),
        '1992': (),
        '1993': ('1993',),
        '1994': ('1993E1',),
        '1995': ('1995',),
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

    for session in year_mapping[year]:
        for bill in scrape_session(chamber, session):
            yield bill

if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
