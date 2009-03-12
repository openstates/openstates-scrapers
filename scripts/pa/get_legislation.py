#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import run_legislation_scraper

def scrape_session(chamber, year, session=0):
    if chamber == 'upper':
        bill_abbr = 'S'
    elif chamber == 'lower':
        bill_abbr = 'H'

    assert int(year) >= 1969, "no data available before 1969"
    assert int(year) <= dt.date.today().year, "can't look into the future"

    # Get session years
    if int(year) % 2 == 1:
        y1 = year
        y2 = str(int(year) + 1)
    else:
        # If second year of session just ignore
        return
    
    url = 'http://www.legis.state.pa.us/cfdocs/legis/bi/BillIndx.cfm?sYear=%s&sIndex=%i&bod=%s' % (y1, session, bill_abbr)
    print url
    soup = BeautifulSoup(urllib2.urlopen(url).read())

    re_str = "body=%s&type=B&bn=\d+" % bill_abbr
    links = soup.findAll(href=re.compile(re_str))

    for link in links:
        bill_number = link.contents[0]
        bill_id = bill_abbr + 'B' + bill_number

        info_url = 'http://www.legis.state.pa.us/cfdocs/billinfo/billinfo.cfm?syear=%s&sind=%i&body=%s&type=B&BN=%s' % (y1, session, bill_abbr, bill_number)
        print info_url
        
        info_page = BeautifulSoup(urllib2.urlopen(info_url).read())
        pn_table = info_page.find('div', {"class": 'pn_table'})
        
        # Latest printing should be listed first
        text_link = pn_table.find('a', href=re.compile('pn=\d{4}'))
        bill_url = 'http://www.legis.state.pa.us%s' % text_link['href']

        yield {'state':'PA', 'chamber':chamber, 'session':'%s-%s' % (y1, y2),
               'bill_id':bill_id, 'remote_url':bill_url}

def scrape_year(chamber, year):
    for session in xrange(0, 4):
        for bill in scrape_session(chamber, year, session):
            yield bill
        
if __name__ == '__main__':
    run_legislation_scraper(scrape_year)
