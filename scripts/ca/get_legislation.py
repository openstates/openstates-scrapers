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

        # Get the history page (following a link from the details page).
        # Once again, we remove tags that BeautifulSoup chokes on
        # (including all meta tags, because bills with quotation marks
        # in the title come to us w/ malformed meta tags)
        hist_link = details.find(href=re.compile("_history.html"))
        hist_url = 'http://www.leginfo.ca.gov%s' % hist_link['href']
        history_raw = urllib2.urlopen(hist_url).read()
        history_raw = history_raw.replace('<! ****** document data starts here ******>', '')
        rem_meta = re.compile('</title>.*</head>', re.MULTILINE | re.DOTALL)
        history_raw = rem_meta.sub('</title></head>', history_raw)
        history = BeautifulSoup(history_raw)

        # Find title and add bill
        title_match = re.search('TOPIC\t:\s(\w.+\n(\t\w.*\n){0,})', history_raw, re.MULTILINE)
        bill_title = title_match.group(1).replace('\n', '').replace('\t', ' ')
        self.add_bill(chamber, session, bill_id, bill_title)

        # Find author (primary sponsor)
        sponsor_match = re.search('^AUTHOR\t:\s(.*)$', history_raw, re.MULTILINE)
        bill_sponsor = sponsor_match.group(1)
        self.add_sponsorship(chamber, session, bill_id, 'primary', bill_sponsor)

        # Get all versions of the bill
        text_re = '%s_%s_bill\w*\.html' % (bill_id[:2].lower(), bill_id[2:])
        links = details.find(text='Bill Text').parent.findAllNext(href=re.compile(text_re))
        for link in links:
            version_url = "http://www.leginfo.ca.gov%s" % link['href']

            # This name is not necessarily unique (for example, there may
            # be many versions called simply "Amended"). Perhaps we should
            # add a date or something to make it unique?
            version_name = link.parent.previousSibling.previousSibling.b.font.string
            self.add_bill_version(chamber, session, bill_id,
                                  version_name, version_url)

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
