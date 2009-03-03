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
    # This function gets legislation from the entire 2-year session that year
    # is a part of because it's much more efficient than going year by year.
    
    if chamber == 'upper':
        chamber_name = 'senate'
        bill_abbr = 'SB'
    elif chamber == 'lower':
        chamber_name = 'assembly'
        bill_abbr = 'AB'

    assert int(year) >= 1993, "no data available before 1993"
    assert int(year) <= dt.date.today().year, "can't look into the future"

    if int(year) % 2 == 1:
        y1 = year[2:]
        if int(year) == 1999:
            y2 = "00"
        else:
            y2 = '%02d' % (int(year[2:]) + 1)
    else:
        y1 = '%02d' % (int(year[2:]) - 1)
        y2 = year[2:]
    
    url = "http://www.leginfo.ca.gov/pub/%s-%s/bill/index_%s_author_bill_topic" % (y1, y2, chamber_name)
    print url
    req = urllib2.Request(url)
    response = urllib2.urlopen(url)
    doc = response.read()
    bill_re = re.compile('\s+(%s\s+\d+)(.*(\n\s{31}.*){0,})' % bill_abbr,
                         re.MULTILINE)

    for match in bill_re.finditer(doc):
        bill_id = match.group(1).replace(' ', '')

        # The URL for the text of the bill contains a date which we
        # can't get from the bill list, so we get the detail page
        # for each bill individually and scrape it from there
        detail_url = 'http://www.leginfo.ca.gov/cgi-bin/postquery?bill_number=%s_%s&sess=%s%s' % (bill_abbr.lower(), bill_id[2:], y1, y2)
        print detail_url
        
        details = urllib2.urlopen(detail_url).read()

        # BeautifulSoup chokes on this malformed tag
        details = details.replace('<P ALIGN=CENTER">', '')
        soup = BeautifulSoup(details)
        
        text_re = '%s_%s_bill\w*\.html' % (bill_abbr.lower(), bill_id[2:])
        links = soup.findAll(href=re.compile(text_re))

        # Get the most recent version (last link)
        bill_url = "http://www.leginfo.ca.gov%s" % links[-1]['href']

        yield {'state':'CA', 'chamber':chamber, 'session':'%s-%s' % (y1, y2),
               'bill_id':bill_id, 'remote_url':bill_url}
        
if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
