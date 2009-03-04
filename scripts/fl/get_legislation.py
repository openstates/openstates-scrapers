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
    if chamber == 'upper':
        chamber_name = 'Senate'
        bill_abbr = 'S'
    elif chamber == 'lower':
        chamber_name = 'House'
        bill_abbr = 'H'

    assert int(year) >= 1998, "no data available before 1998"
    assert int(year) <= dt.date.today().year, "can't look into the future"

    base_url = 'http://www.flsenate.gov/Session/index.cfm?Mode=Bills&BI_Mode=ViewBySubject&Letter=%s&Year=%s&Chamber=%s'
    
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        url = base_url % (letter, year, chamber_name)
        print url
        soup = BeautifulSoup(urllib2.urlopen(url).read())
        bill_re = re.compile("%s (\d{4})" % bill_abbr)
        
        for b in soup.findAll('b'):
            if not b.string:
                continue
            
            match = bill_re.search(b.string)
            if match:
                bill_id = match.group(0)
                bill_number = match.group(1)
                
                if chamber == 'upper':
                    bill_file = "sb%s.html" % bill_number
                else:
                    bill_file = "hb%s00.html" % bill_number
                    
                bill_url = 'http://www.flsenate.gov/cgi-bin/view_page.pl?File=%s&Directory=session/%s/%s/bills/billtext/html/' % (bill_file, year, chamber_name)

                yield {'state':'FL', 'chamber':chamber, 'session':year,
                       'bill_id':bill_id, 'remote_url':bill_url}

if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
