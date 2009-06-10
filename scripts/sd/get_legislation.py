#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import *

class SDLegislationScraper(LegislationScraper):

    state = 'sd'

    metadata = {
        'state_name': 'South Dakota',
        'legislature_name': 'South Dakota State Legislature',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Representative',
        'upper_term': 2,
        'lower_term': 2,
        'sessions': ['1997', '1998', '1999', '2000', '2001', '2002', '2003',
                     '2004', '2005', '2006', '2007', '2008', '2009'],
        'session_details': {
            '1997': {'years': [1997], 'election_year': 1996,
                     'sub_sessions': ['1997s'], 'alternate': '72nd'},
            '1998': {'years': [1998], 'election_year': 1996,
                     'sub_sessions': [], 'alternate': '73rd'},
            '1999': {'years': [1999], 'election_year': 1998,
                     'sub_sessions': [], 'alternate': '74th'},
            '2000': {'years': [2000], 'election_year': 1998,
                     'sub_sessions': ['2000s'], 'alternate': '75th'},
            '2001': {'years': [2001], 'election_year': 2000,
                     'sub_sessions': ['2001s'], 'alternate': '76th'},
            '2002': {'years': [2002], 'election_year': 2000,
                     'sub_sessions': [], 'alternate': '77th'},
            '2003': {'years': [2003], 'election_year': 2002,
                     'sub_sessions': ['2003s'], 'alternate': '78th'},
            '2004': {'years': [2004], 'election_year': 2002,
                     'sub_sessions': [], 'alternate': '79th'},
            '2005': {'years': [2005], 'election_year': 2004,
                     'sub_sessions': ['2005s'], 'alternate': '80th'},
            '2006': {'years': [2006], 'election_year': 2004,
                     'sub_sessions': [], 'alternate': '81st'},
            '2007': {'years': [2007], 'election_year': 2006,
                     'sub_sessions': [], 'alternate': '82nd'},
            '2008': {'years': [2008], 'election_year': 2006,
                     'sub_sessions': [], 'alternate': '83rd'},
            '2009': {'years': [2009], 'election_year': 2008,
                     'sub_sessions': [], 'alternate': '84th'},
            }
        }
    
    # The format of SD's legislative info pages changed in 2009, so we have
    # two separate scrapers.

    def scrape_new_session(self, chamber, session):
        """
        Scrapes SD's bill data from 2009 on.
        """

        if chamber == 'upper':
            bill_abbr = 'SB'
        elif chamber == 'lower':
            bill_abbr = 'HB'

        # Get bill list page
        session_url = 'http://legis.state.sd.us/sessions/%s/' % session
        bill_list_url = session_url + 'BillList.aspx'
        self.log('Getting bill list for %s %s' % (chamber, session))
        bill_list = BeautifulSoup(self.urlopen(bill_list_url))

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

            # Download history page
            hist_url = session_url + bill_link['href']
            history = BeautifulSoup(self.urlopen(hist_url))

            bill = Bill(session, chamber, bill_id, bill_name)

            # Get all bill versions
            text_table = history.findAll('table')[1]
            for row in text_table.findAll('tr')[2:]:
                #version_date = row.find('td').string
                version_path = row.findAll('td')[1].a['href']
                version_url = "http://legis.state.sd.us/sessions/%s/%s" % (
                    session, version_path)

                version_name = row.findAll('td')[1].a.string.strip()

                bill.add_version(version_name, version_url)

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
                bill.add_action(chamber, action, act_date)

            self.add_bill(bill)

    def scrape_old_session(self, chamber, session):
        """
        Scrape SD's bill data from 1997 through 2008.
        """

        if chamber == 'upper':
            bill_abbr = 'SB'
        else:
            bill_abbr = 'HB'

        # Get bill list page (and replace malformed tags that some versions of
        # BeautifulSoup choke on)
        session_url = 'http://legis.state.sd.us/sessions/%s/' % session
        bill_list_url = session_url + 'billlist.htm'
        self.log("Getting bill list for %s %s" % (chamber, session))
        bill_list_raw = self.urlopen(bill_list_url)
        bill_list_raw = bill_list_raw.replace('BORDER= ', '').replace('"</A>', '"></A>')
        bill_list = BeautifulSoup(bill_list_raw)

        # Bill and text link formats
        bill_re = re.compile('%s (\d+)' % bill_abbr)
        text_re = re.compile('/sessions/%s/bills/%s.*\.htm' % (session, bill_abbr), re.IGNORECASE)
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

            # Get history page (replacing malformed tag)
            hist_url = session_url + bill_link['href']
            history_raw = self.urlopen(hist_url)
            history_raw = history_raw.replace('BORDER=>', '>')
            history = BeautifulSoup(history_raw)

            # Get URL of latest verion of bill (should be listed last)
            bill_url = history.findAll('a', href=text_re)[-1]['href']
            bill_url = 'http://legis.state.sd.us%s' % bill_url

            # Add bill
            bill = Bill(session, chamber, bill_id, bill_name)

            # Get bill versions
            text_table = history.findAll('table')[1]
            for row in text_table.findAll('tr')[2:]:
                #version_date = row.find('td').string
                version_path = row.findAll('td')[1].a['href']
                version_url = "http://legis.state.sd.us" + version_path

                version_name = row.findAll('td')[1].a.string.strip()

                bill.add_version(version_name, version_url)

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
                bill.add_action(chamber, action, act_date)

            self.add_bill(bill)

    def scrape_bills(self, chamber, year):
        if year not in self.metadata['session_details']:
            raise NoDataForYear(year)

        if int(year) >= 2009:
            self.scrape_new_session(chamber, year)
            for sub in self.metadata['session_details'][year]['sub_sessions']:
                self.scrape_new_session(chamber, sub)
        else:
            self.scrape_old_session(chamber, year)
            for sub in self.metadata['session_details'][year]['sub_sessions']:
                self.scrape_old_session(chamber, sub)

    def scrape_legislators(self, chamber, year):
        if year not in self.metadata['session_details']:
            raise NoDataForYear(year)
        
if __name__ == '__main__':
    SDLegislationScraper().run()
