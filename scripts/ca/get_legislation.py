#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class CALegislationScraper(LegislationScraper):

    state = 'ca'

    def get_bill_info(self, chamber, session, bill_id):
        print 'Getting %s %s' % (session, bill_id)

        detail_url = 'http://www.leginfo.ca.gov/cgi-bin/postquery?bill_number=%s_%s&sess=%s' % (bill_id[:2].lower(), bill_id[2:], session.replace('-', ''))

        # Get the details page and parse it with BeautifulSoup. These
        # pages contain a malformed 'p' tag that (certain versions of)
        # BS choke on, so we replace it with a regex before parsing.
        details_raw = urllib2.urlopen(detail_url).read()
        details_raw = details_raw.replace('<P ALIGN=CENTER">', '')
        details = BeautifulSoup(details_raw)

        # Get the URL of the text of the most recent version of this bill
        # (it should be the last link with the given target format).
        text_re = '%s_%s_bill\w*\.html' % (bill_id[:2].lower(), bill_id[2:])
        links = details.findAll(href=re.compile(text_re))
        bill_url = "http://www.leginfo.ca.gov%s" % links[-1]['href']

        # Get the history page (following a link from the details page).
        # Once again, there's a tag that BeautifulSoup chokes on.
        hist_link = details.find(href=re.compile("_history.html"))
        hist_url = 'http://www.leginfo.ca.gov%s' % hist_link['href']
        history_raw = urllib2.urlopen(hist_url).read()
        history_raw = history_raw.replace('<! ****** document data starts here ******>', '')
        history = BeautifulSoup(history_raw)

        # Find title and add bill
        # Note: this fails on a few bills that have quotation marks in their
        # titles because CA's site outputs malformed meta tags for them.
        # (see 07-08 AB528 @ http://www.leginfo.ca.gov/pub/07-08/bill/asm/ab_0501-0550/ab_528_bill_20080201_history.html
        # Will fix later.
        bill_sponsor = history.find('meta', attrs={'name':'AUTHOR'})['content'].strip()
        bill_name = history.find('meta', attrs={'name':'TOPIC'})['content'].strip()
        self.add_bill(chamber, session, bill_id, bill_name)
        self.add_bill_version(chamber, session, bill_id, 'latest', bill_url)
        self.add_sponsorship(chamber, session, bill_id, 'primary', bill_sponsor)

        # Get bill actions
        action_re = re.compile('(\d{4})|([\w.]{4,6}\s+\d{1,2})\s+(.*(\n\s+.*){0,})', re.MULTILINE)
        act_year = None
        for act_match in action_re.finditer(history.find('pre').contents[0]):
            # If we didn't match group 2 then this must be a year change
            if act_match.group(2) == None:
                act_year = act_match.group(1)
                continue

            # If not year change, must be an action
            act_date = act_match.group(2)
            action = act_match.group(3).replace('\n', '').replace('  ', ' ').replace('\t', ' ')
            self.add_action(chamber, session, bill_id, chamber,
                            action, act_date)

    def scrape_session(self, chamber, session):
        if chamber == 'upper':
            chamber_name = 'senate'
            bill_abbr = 'SB'
        elif chamber == 'lower':
            chamber_name = 'assembly'
            bill_abbr = 'AB'

        # Get the list of all chamber bills for the given session
        # (text format, sorted by author)
        url = "http://www.leginfo.ca.gov/pub/%s/bill/index_%s_author_bill_topic" % (session, chamber_name)
        print "Getting: %s" % url
        bill_list = urllib2.urlopen(url).read()
        bill_re = re.compile('\s+(%s\s+\d+)(.*(\n\s{31}.*){0,})' % bill_abbr,
                             re.MULTILINE)

        for bill_match in bill_re.finditer(bill_list):
            bill_id = bill_match.group(1).replace(' ', '')
            self.get_bill_info(chamber, session, bill_id)

    def scrape_bills(self, chamber, year):
        # CA makes data available from 1993 on
        if int(year) < 1993 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # We expect the first year of a session (odd)
        if int(year) % 2 != 1:
            raise NoDataForYear(year)

        year1 = year[2:]
        year2 = str((int(year) + 1))[2:]
        session = "%s-%s" % (year1, year2)

        self.scrape_session(chamber, session)

if __name__ == '__main__':
    CALegislationScraper().run()
