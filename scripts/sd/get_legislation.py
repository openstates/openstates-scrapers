#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class SDLegislationScraper(LegislationScraper):

    state = 'sd'
    
    # The format of SD's legislative info pages changed in 2009, so we have
    # two separate scrapers.

    def new_scraper(self, chamber, year):
        """
        Scrapes SD's bill data from 2009 on.
        """

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
        date_re = re.compile('\d{2}/\d{2}/\d{4}')

        for bill_link in bill_list.findAll('a'):
            if not bill_link.string:
                # Empty link
                continue

            bill_match = bill_re.match(bill_link.string)
            if not bill_match:
                # Not a bill link
                continue

            # Parse bill ID and name
            bill_id = bill_link.string.replace('&nbsp;', ' ')
            bill_name = bill_link.findNext().string
            print "Getting %s: %s" % (bill_id, bill_name)

            # Download history page
            hist_url = session_url + bill_link['href']
            history = BeautifulSoup(urllib2.urlopen(hist_url).read())

            # The version table contains links to all available bill texts
            # Should be sorted by date, so we grab the first one
            version_table = history.find(id='ctl00_contentMain_ctl00_tblBillVersions')
            bill_url = session_url + version_table.find('a')['href']

            # Add bill
            self.add_bill(chamber, year, bill_id, bill_name)
            self.add_bill_version(chamber, year, bill_id, 'latest',
                                  bill_url)

            # Get actions
            act_table = history.find('table')
            for act_row in act_table.findAll('td'):
                if not act_row.findChild(0) or not act_row.findChild(0).string:
                    continue

                # Get the date (if can't find one then this isn't an action)
                date_match = date_re.match(act_row.findChild(0).string)
                if not date_match:
                    continue
                act_date = date_match.group(0)

                # Get the action string
                action = ""
                for node in act_row.findChild(0).findNext().contents:
                    if node.string:
                        action += node.string
                    else:
                        action += node
                action = action.strip()

                # Add action
                self.add_action(chamber, year, bill_id, chamber, action,
                                act_date)

    def old_scraper(self, chamber, year):
        """
        Scrape SD's bill data from 1997 through 2008.
        """

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
        bill_list_raw = bill_list_raw.replace('BORDER= ', '').replace('"</A>', '"></A>')
        bill_list = BeautifulSoup(bill_list_raw)

        # Bill and text link formats
        bill_re = re.compile('%s (\d+)' % bill_abbr)
        text_re = re.compile('/sessions/%s/bills/%s.*\.htm' % (year, bill_abbr), re.IGNORECASE)
        date_re = re.compile('\d{2}/\d{2}/\d{4}')

        for bill_link in bill_list.findAll('a'):
            if not bill_link.string:
                # Empty link
                continue

            bill_match = bill_re.match(bill_link.string)
            if not bill_match:
                # Not bill link
                continue

            # Get the bill ID and name
            bill_id = bill_link.string
            bill_name = bill_link.findNext().string
            print "Getting %s: %s" % (bill_id, bill_name)

            # Get history page (replacing malformed tag)
            hist_url = session_url + bill_link['href']
            history_raw = urllib2.urlopen(hist_url).read()
            history_raw = history_raw.replace('BORDER=>', '>')
            history = BeautifulSoup(history_raw)

            # Get URL of latest verion of bill (should be listed last)
            bill_url = history.findAll('a', href=text_re)[-1]['href']
            bill_url = 'http://legis.state.sd.us%s' % bill_url

            # Add bill
            self.add_bill(chamber, year, bill_id, bill_name)
            self.add_bill_version(chamber, year, bill_id, 'latest',
                                  bill_url)

            # Get actions
            act_table = history.find('table')
            for act_row in act_table.findAll('td'):
                if not act_row.findChild(0) or not act_row.findChild(0).string:
                    continue

                # Get the date (if can't find one then this isn't an action)
                date_match = date_re.match(act_row.findChild(0).string)
                if not date_match:
                    continue
                act_date = date_match.group(0)

                # Get the action string
                action = ""
                for node in act_row.findChild(0).findNext().contents:
                    if node.string:
                        action += node.string
                    else:
                        action += node
                action = action.strip()

                # Add action
                self.add_action(chamber, year, bill_id, chamber, action,
                                act_date)

    def scrape_bills(self, chamber, year):
        # Data available for 1997 on
        if int(year) < 1997 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        if int(year) >= 2009:
            self.new_scraper(chamber, year)
        else:
            self.old_scraper(chamber, year)
        
if __name__ == '__main__':
    SDLegislationScraper().run()
