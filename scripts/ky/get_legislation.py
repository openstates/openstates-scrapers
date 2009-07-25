#!/usr/bin/env python
import urllib, urllib2
import re
from BeautifulSoup import BeautifulSoup

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import run_legislation_scraper

def scrape_session(chamber, session):
    if chamber == 'upper':
        chamber_abbr = 'H'
        bill_abbr = 'HB'
    elif chamber == 'lower':
        chamber_abbr = 'S'
        bill_abbr = 'SB'

    index_file = "http://www.lrc.ky.gov/record/%s/bills_%s.htm" % (session, chamber_abbr)
    print index_file
    req = urllib2.Request(index_file)
    response = urllib2.urlopen(req)
    doc = response.read()
    soup = BeautifulSoup(doc)
    re_str = "%s\d{1,4}.htm" % bill_abbr
    links = soup.findAll(href=re.compile(re_str))

    for link in links:
        bill_id = link['href'].replace('.htm', '')
        bill_url = "http://www.lrc.ky.gov/recarch/%s/%s" % (session, link['href'])

        #if download:
        #    local_filename = 'data/ky/legislation/%s%s%s.htm' % (chamber, session, bill_id) 
        #    urllib.urlretrieve(bill_url, local_filename)
        #    time.sleep(0.5)

        yield {'state':'KY', 'chamber':chamber, 'session':session,
               'bill_id':bill_id, 'remote_url':bill_url}

def scrape_legislation(chamber, year):
    yy = str(year)[2:]
    for session in ['%sRS','%sSS','%sS2']:
        for bill in scrape_session(chamber, session % yy):
            yield bill

if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
