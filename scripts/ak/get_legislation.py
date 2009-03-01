#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import run_legislation_scraper

def scrape_legislation(chamber, year):
    # What about joint resolutions, etc.? Just ignoring them for now.
    if chamber == 'upper':
        bill_abbr = 'SB'
    elif chamber == 'lower':
        bill_abbr = 'HB'

    # BASIS has data from 1993, it's not clear if earlier data
    # is available online anywhere.
    assert int(year) >= 1993, "no data available before 1993"
    assert int(year) <= dt.date.today().year, "can't look into the future"

    # Sessions last 2 years, 1993-1994 was the 18th
    session = 18 + ((int(year) - 1993) / 2)
    
    date1 = '0101' + year[2:]
    date2 = '1231' + year[2:]

    url = 'http://www.legis.state.ak.us/basis/range_multi.asp?session=%i&date1=%s&date2=%s' % (session, date1, date2)
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    doc = response.read()
    soup = BeautifulSoup(doc)

    re_str = "bill=%s\d+" % bill_abbr
    links = soup.findAll(href=re.compile(re_str))

    for link in links:
        bill_id = link.contents[0].replace(' ', '')

        # This is the URL for the bill as it was introduced.
        # How should revisions be handled?
        bill_url = 'http://www.legis.state.ak.us/basis/get_bill_text.asp?hsid=%s%04dA&session=%i' % (bill_abbr, int(bill_id[2:]), session)

        yield {'state':'AK', 'chamber':chamber, 'session':session,
               'bill_id':bill_id, 'remote_url':bill_url}

if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
