#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import *

class PALegislationScraper(LegislationScraper):

    state = 'pa'

    metadata = {
        'state_name': 'Pennsylvania',
        'legislature_name': 'Pennsylvania General Assembly',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Representative',
        'upper_term': 4,
        'lower_term': 2,
        'sessions': [],
        'session_details': {},
        }

    def scrape_metadata(self):
        session_page = BeautifulSoup(self.urlopen("http://www.legis.state.pa.us/cfdocs/legis/home/session.cfm"))

        for option in session_page.find(id="BTI_sess").findAll('option'):
            if option['value'].endswith('_0'):
                year1 = int(option['value'][1:5])
                year2 = year1 + 1
                session = "%d-%d" % (year1, year2)
            
                self.metadata['sessions'].append(session)
                self.metadata['session_details'][session] = {
                    'years': [year1, year2],
                    'election_year': year1 - 1,
                    'sub_sessions': [],
                    }
            else:
                session = option.string[0:9]
                self.metadata['session_details'][session][
                    'sub_sessions'].append(option.string)

        # sessions were in reverse-chronological order
        self.metadata['sessions'].reverse()

        return self.metadata

    def scrape_session(self, chamber, session, special=0):
        if chamber == 'upper':
            bill_abbr = 'S'
        elif chamber == 'lower':
            bill_abbr = 'H'

        # Session years
        year1 = session[0:4]

        # Get the bill list
        bill_list_url = 'http://www.legis.state.pa.us/cfdocs/legis/bi/BillIndx.cfm?sYear=%s&sIndex=%i&bod=%s' % (year1, special, bill_abbr)
        self.log("Getting bill list for %s %s" % (chamber, session))
        bill_list = BeautifulSoup(self.urlopen(bill_list_url))

        # Get all bill links
        re_str = "body=%s&type=(B|R)&bn=\d+" % bill_abbr
        links = bill_list.findAll(href=re.compile(re_str))

        for link in links:
            bill_number = link.contents[0]
            type = re.search('type=(B|R)', link['href']).group(1)
            bill_id = "%s%s %s" % (bill_abbr, type, bill_number)

            # Get info page
            info_url = 'http://www.legis.state.pa.us/cfdocs/billinfo/billinfo.cfm?syear=%s&sind=%i&body=%s&type=%s&BN=%s' % (year1, special, bill_abbr, type, bill_number)
            info_page = BeautifulSoup(self.urlopen(info_url))

            # Get bill title
            title_label = info_page.find(text='Short Title:')
            bill_title = title_label.findNext().string

            # Add bill
            bill = Bill(session, chamber, bill_id, bill_title)

            # Get bill versions
            pn_table = info_page.find('div', {"class": 'pn_table'})
            text_rows = pn_table.findAll('tr')[1:]
            for tr in text_rows:
                text_link = tr.td.a
                text_url = 'http://www.legis.state.pa.us%s' % text_link['href']
                bill.add_version(text_link.string.strip(), text_url)

            history_url = 'http://www.legis.state.pa.us/cfdocs/billinfo/bill_history.cfm?syear=%s&sind=%i&body=%s&type=%s&BN=%s' % (year1, special, bill_abbr, type, bill_number)
            self.scrape_history(bill, history_url)
            self.add_bill(bill)

    def scrape_history(self, bill, url):
        """
        Given a bill and the url of its history page, scrape all
        historical information (actions and sponsors) related to that bill.
        """
        history = BeautifulSoup(self.urlopen(url))

        self.scrape_sponsors(bill, history)

        act_table = history.find(text="Actions:").parent.findNextSibling()
        self.scrape_actions(bill, act_table)

    def scrape_sponsors(self, bill, history):
        # Sponsor format changed in 2009
        year1 = bill['session'][0:4]
        if int(year1) < 2009:
            sponsors = history.find(text='Sponsors:').parent.findNext('td').find('td').string.strip().replace(' and', ',').split(', ')
            bill.add_sponsor('primary', sponsors[0])
            for sponsor in sponsors[1:]:
                bill.add_sponsor('cosponsor', sponsor)
        else:
            sponsors = history.find(text='Sponsors:').parent.findNext().findAll('a')
            bill.add_sponsor('primary', sponsors[0].string)
            for sponsor in sponsors[1:]:
                bill.add_sponsor('cosponsor', sponsor.string)

    def scrape_actions(self, bill, act_table):
        act_chamber = bill['chamber']
        for row in act_table.findAll('tr'):
            act_raw = ""
            for node in row.td.div:
                if hasattr(node, 'contents'):
                    act_raw += node.contents[0]
                else:
                    act_raw += node
            act_raw = act_raw.replace('&#160;', ' ')
            act_match = re.match('(.*),\s+((\w+\.?) (\d+), (\d{4}))', act_raw)
            if act_match:
                bill.add_action(act_chamber, act_match.group(1),
                                act_match.group(2).strip())
            else:
                # Handle actions from the other chamber
                # ("In the (House|Senate)" row followed by actions that
                # took place in that chamber)
                cham_match = re.match('In the (House|Senate)', act_raw)
                if not cham_match:
                    # Ignore?
                    continue

                if cham_match.group(1) == 'House':
                    act_chamber = 'lower'
                else:
                    act_chamber = 'upper'

    def scrape_bills(self, chamber, year):
        session = "%s-%d" % (year, int(year) + 1)
        if not session in self.metadata['session_details']:
            raise NoDataForYear(year)

        self.scrape_session(chamber, session)
        for special in self.metadata['session_details'][session]['sub_sessions']:
            session_num = re.search('#(\d+)', special).group(1)
            self.scrape_session(chamber, session, special)

    def scrape_legislators(self, chamber, year):
        pass

if __name__ == '__main__':
    PALegislationScraper().run()
