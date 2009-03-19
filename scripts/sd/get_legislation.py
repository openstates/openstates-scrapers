#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import run_legislation_scraper

# The format of SD's legislative info pages changed in 2009, so we have
# two separate scrapers.

def new_scraper(chamber, year):
    """
    Scrapes SD's bill data from 2009 on.
    """

    # Only use for post-2009
    assert int(year) >= 2009, "no data available before 2009"
    assert int(year) <= dt.date.today().year, "can't look into the future"
    
    if chamber == 'upper':
        bill_abbr = 'SB'
    elif chamber == 'lower':
        bill_abbr = 'HB'

    # Get bill list page
    session_url = 'http://legis.state.sd.us/sessions/%s/' % year
    bill_list_url = session_url + 'BillList.aspx'
    bill_list = BeautifulSoup(urllib2.urlopen(bill_list_url).read())

    # Format of bill link contents
    bill_re = re.compile('%s&nbsp;(\d+)' % bill_abbr)

    for bill_link in bill_list.findAll('a'):
        if not bill_link.string:
            # Empty link
            continue

        bill_match = bill_re.match(bill_link.string)
        if not bill_match:
            # Not a bill link
            continue

        # Parse bill ID
        bill_id = bill_link.string.replace('&nbsp;', ' ')
        print "Getting %s" % bill_id

        # Download history page
        hist_url = session_url + bill_link['href']
        history = BeautifulSoup(urllib2.urlopen(hist_url).read())

        # The version table contains links to all available bill texts
        # Should be sorted by date, so we grab the first one
        version_table = history.find(id='ctl00_contentMain_ctl00_tblBillVersions')
        bill_url = session_url + version_table.find('a')['href']
        
        yield {'state':'SD', 'chamber':chamber, 'session':year,
               'bill_id':bill_id, 'remote_url':bill_url}

def old_scraper(chamber, year):
    """
    Scrape SD's bill data from 1997 through 2008.
    """

    # Only use for old data
    assert int(year) >= 1997, "no data available before 1997"
    assert int(year) <= 2008, "no data available after 2008"
    
    if chamber == 'upper':
        bill_abbr = 'SB'
    else:
        bill_abbr = 'HB'

    # Get bill list page (and replace malformed tags that some versions of
    # BeautifulSoup choke on)
    session_url = 'http://legis.state.sd.us/sessions/%s/' % year
    bill_list_url = session_url + 'billlist.htm'
    print bill_list_url
    bill_list_raw = urllib2.urlopen(bill_list_url).read()
    bill_list_raw = bill_list_raw.replace('BORDER= ', '')
    bill_list = BeautifulSoup(bill_list_raw)
    
    # Bill and text link formats
    bill_re = re.compile('%s (\d+)' % bill_abbr)
    text_re = re.compile('<a href="(/sessions/%s/Bills/%s\w+\.htm)"' % (year, bill_abbr))

    for bill_link in bill_list.findAll('a'):
        if not bill_link.string:
            # Empty link
            continue

        bill_match = bill_re.match(bill_link.string)
        if not bill_match:
            # Not bill link
            continue

        bill_id = bill_link.string
        print "Getting %s" % bill_id

        # Get history page
        hist_url = session_url + bill_link['href']
        history = urllib2.urlopen(hist_url).read()
        print hist_url

        # Latest version of BeautifulSoup has trouble with the second half
        # of this document, so for now we'll just use a regex
        hist_match = text_re.search(history)
        bill_url = 'http://legis.state.sd.us' + hist_match.group(1)

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
