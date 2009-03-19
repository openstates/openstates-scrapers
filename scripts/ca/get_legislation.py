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
        chamber_name = 'senate'
        bill_abbr = 'SB'
    elif chamber == 'lower':
        chamber_name = 'assembly'
        bill_abbr = 'AB'

    # leginfo.ca.gov has data from 1993 on
    assert int(year) >= 1993, "no data available before 1993"
    assert int(year) <= dt.date.today().year, "can't look into the future"

    if int(year) % 2 == 1:
        # Turn the first year of a session into year1, year2 pair
        y1 = year[2:]
        y2 = str(int(year) + 1)[2:]
    else:
        # If second year of session just ignore
        return

    # Get the list of all chamber bills for the given session
    # (text format, sorted by author)
    url = "http://www.leginfo.ca.gov/pub/%s-%s/bill/index_%s_author_bill_topic" % (y1, y2, chamber_name)
    print "Getting: %s" % url
    bill_list = urllib2.urlopen(url).read()
    bill_re = re.compile('\s+(%s\s+\d+)(.*(\n\s{31}.*){0,})' % bill_abbr,
                         re.MULTILINE)

    for bill_match in bill_re.finditer(bill_list):
        bill_id = bill_match.group(1).replace(' ', '')
        print "Getting %s" % bill_id
        
        # The URL for the text of the bill contains a date which we
        # can't get from the bill list, so we get the detail page
        # for each bill individually and scrape it from there
        detail_url = 'http://www.leginfo.ca.gov/cgi-bin/postquery?bill_number=%s_%s&sess=%s%s' % (bill_abbr.lower(), bill_id[2:], y1, y2)

        # Get the details page and parse it with BeautifulSoup.
        # These pages contain a malformed 'p' tag that (certain versions of)
        # BeautifulSoup choke on, so we replace it with a regex before parsing.
        details_raw = urllib2.urlopen(detail_url).read()
        details_raw = details_raw.replace('<P ALIGN=CENTER">', '')
        details = BeautifulSoup(details_raw)

        # Get the URL of the text of the most recent version of this bill
        # (it should be the last link with the given target format).
        text_re = '%s_%s_bill\w*\.html' % (bill_abbr.lower(), bill_id[2:])
        links = details.findAll(href=re.compile(text_re))
        bill_url = "http://www.leginfo.ca.gov%s" % links[-1]['href']

        # Get the history page (following a link from the details page).
        # Once again, there's a tag that BeautifulSoup chokes on.
        hist_link = details.find(href=re.compile("_history.html"))
        hist_url = 'http://www.leginfo.ca.gov%s' % hist_link['href']
        history_raw = urllib2.urlopen(hist_url).read()
        history_raw = history_raw.replace('<! ****** document data starts here ******>', '')
        history = BeautifulSoup(history_raw)

        # Find sponsor and title
        bill_sponsor = history.find('meta', attrs={'name':'AUTHOR'})['content'].strip()
        bill_name = history.find('meta', attrs={'name':'TOPIC'})['content'].strip()

        # Get bill actions
        action_re = re.compile('(\d{4})|([\w.]{4,6}\s+\d{1,2})\s+(.*(\n\s+.*){0,})', re.MULTILINE)
        act_year = None
        for act_match in action_re.finditer(history.find('pre').contents[0]):
            # If we didn't match group 2 then this must be a year change
            if act_match.group(2) == None:
                act_year = act_match.group(1)
                continue

            # Must be an action
            act_date = act_match.group(2)
            action = act_match.group(3).replace('\n', '').replace('  ', ' ').replace('\t', ' ')

        yield {'state':'CA', 'chamber':chamber, 'session':'%s-%s' % (y1, y2),
               'bill_id':bill_id, 'remote_url':bill_url}
        
if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
