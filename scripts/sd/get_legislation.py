#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import run_legislation_scraper

def new_scraper(chamber, year):
    """
    Scrapes SD's bill data from 2009 on.
    """
    assert int(year) >= 2009, "no data available before 2009"
    assert int(year) <= dt.date.today().year, "can't look into the future"
    
    if chamber == 'upper':
        bill_abbr = 'SB'
    elif chamber == 'lower':
        bill_abbr = 'HB'

    session_url = 'http://legis.state.sd.us/sessions/%s/' % year
    url = session_url + 'BillList.aspx'
    soup = BeautifulSoup(urllib2.urlopen(url).read())

    bill_re = re.compile('%s&nbsp;(\d+)' % bill_abbr)

    for link in soup.findAll('a'):
        if not link.string:
            continue

        match = bill_re.match(link.string)
        if not match:
            continue
        
        print link['href']
        bill_id = link.string.replace('&nbsp;', ' ')
        
        hist_url = session_url + link['href']
        history = BeautifulSoup(urllib2.urlopen(hist_url).read())
        version_table = history.find(id='ctl00_contentMain_ctl00_tblBillVersions')
        bill_url = session_url + version_table.find('a')['href']
        
        yield {'state':'SD', 'chamber':chamber, 'session':year,
               'bill_id':bill_id, 'remote_url':bill_url}

def old_scraper(chamber, year):
    """
    Scrape SD's bill data from 1997 through 2008.
    """
    assert int(year) >= 1997, "no data available before 1997"
    assert int(year) <= 2008, "no data available after 2008"
    
    if chamber == 'upper':
        bill_abbr = 'SB'
    else:
        bill_abbr = 'HB'

    session_url = 'http://legis.state.sd.us/sessions/%s/' % year
    url = session_url + 'billlist.htm'
    soup = BeautifulSoup(urllib2.urlopen(url).read())

    bill_re = re.compile('%s (\d+)' % bill_abbr)
    text_re = re.compile('<a href="(/sessions/%s/Bills/%s\w+\.htm)"' % (year, bill_abbr))

    for link in soup.findAll('a'):
        if not link.string:
            continue

        match = bill_re.match(link.string)
        if not match:
            continue

        bill_id = link.string

        hist_url = session_url + link['href']
        print hist_url
        history = urllib2.urlopen(hist_url).read()

        # Latest version of BeautifulSoup has trouble with the second half
        # of this document, so for now we'll just use a regex
        match = text_re.search(history)
        bill_url = 'http://legis.state.sd.us' + match.groups()[0]

        yield {'state':'SD', 'chamber':chamber, 'session':year,
               'bill_id':bill_id, 'remote_url':bill_url}

def scrape_legislation(chamber, year):
    if int(year) >= 2009:
        scraper = new_scraper
    else:
        scraper = old_scraper

    for bill in scraper(chamber, year):
        yield bill
        
if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
