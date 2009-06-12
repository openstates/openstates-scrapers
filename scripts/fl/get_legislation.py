#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import *

class FLLegislationScraper(LegislationScraper):

    state = 'fl'

    metadata = {
        'state_name': 'Florida',
        'legislature_name': 'Florida Legislature',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Representative',
        'upper_term': 4,
        'lower_term': 2,
        'sessions': ['1998', '1999', '2000', '2001', '2002', '2003', '2004',
                     '2005', '2006', '2007', '2008', '2009'],
        'session_details': {
            '1998': {'years': [1998], 'sub_sessions': []},
            '1999': {'years': [1999], 'sub_sessions': []},
            '2000': {'years': [2000], 'sub_sessions': ['2000 A', '2000 O']},
            '2001': {'years': [2001],
                     'sub_sessions': ['2001 A', '2001 B', '2001 C']},
            '2002': {'years': [2002],
                     'sub_sessions': ['2002 D', '2002 E', '2002 O']},
            '2003': {'years': [2003], 'sub_sessions': ['2003 A', '2003 B',
                                                       '2003 C', '2003 D',
                                                       '2003 E']},
            '2004': {'years': [2004], 'sub_sessions': ['2004 A', '2004 O']},
            '2005': {'years': [2005], 'sub_sessions': ['2005 B']},
            '2006': {'years': [2006], 'sub_sessions': ['2006 O']},
            '2007': {'years': [2007],
                     'sub_sessions': ['2007 A', '2007 B', '2007 C', '2007 D']},
            '2008': {'years': [2008], 'sub_sessions': ['2008 O']},
            '2009': {'years': [2009], 'sub_sessions': ['2009 A']},
            }
        }

    def scrape_legislators(self, chamber, year):
        if year not in self.metadata['session_details']:
            raise NoDataForYear(year)

    def scrape_session(self, chamber, session):
        if chamber == 'upper':
            chamber_name = 'Senate'
            bill_abbr = 'S'
        elif chamber == 'lower':
            chamber_name = 'House'
            bill_abbr = 'H'

        # Base url for bills sorted by first letter of title
        base_url = 'http://www.flsenate.gov/Session/index.cfm?Mode=Bills&BI_Mode=ViewBySubject&Letter=%s&Year=%s&Chamber=%s'

        # Bill ID format
        bill_re = re.compile("%s (\d{4}[ABCDEO]?)" % bill_abbr)
    
        # Go through all sorted bill list pages
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            bill_list_url = base_url % (letter, session.replace(' ', ''),
                                        chamber_name)
            self.log("Getting bill list for %s %s (%s)" % (chamber, session,
                                                           letter))
            bill_list = BeautifulSoup(self.urlopen(bill_list_url))
            
            # Bill ID's are bold
            for b in bill_list.findAll('b'):
                if not b.string:
                    continue
            
                match = bill_re.search(b.string)
                if match:
                    # Bill ID and number
                    bill_id = match.group(0)
                    bill_number = match.group(1)

                    # Get bill name and info url
                    bill_link = b.parent.findNext('td').a
                    bill_name = bill_link.string.strip()
                    info_url = "http://www.flsenate.gov/Session/%s&Year=%s" % (bill_link['href'], session)

                    # Add bill
                    bill = Bill(session, chamber, bill_id, bill_name)

                    # Get bill info page
                    info_page = BeautifulSoup(self.urlopen(info_url))

                    # Get all bill versions
                    bill_table = info_page.find('a', attrs={'name':'BillText'}).parent.parent.findNext('tr').td.table
                    if bill_table:
                        for tr in bill_table.findAll('tr')[1:]:
                            version_name = tr.td.string
                            version_url = "http://www.flsenate.gov%s" % tr.a['href']
                            bill.add_version(version_name, version_url)

                    # Get actions
                    hist_table = info_page.find('pre', "billhistory")
                    hist = ""
                    for line in hist_table.findAll(text=True):
                        hist += line + "\n"
                    hist = hist.replace('&nbsp;', ' ')
                    act_re = re.compile('^  (\d\d/\d\d/\d\d) (SENATE|HOUSE) (.*\n(\s{16,16}.*\n){0,})', re.MULTILINE)
                    for act_match in act_re.finditer(hist):
                        action = act_match.group(3).replace('\n', ' ')
                        action = re.sub('\s+', ' ', action).strip()
                        if act_match.group(2) == 'SENATE':
                            act_chamber = 'upper'
                        else:
                            act_chamber = 'lower'
                        bill.add_action(act_chamber, action, act_match.group(1))

                    # Get primary sponsor
                    # Right now we just list the committee as the primary sponsor
                    # for committee substituts. In the future, consider listing
                    # committee separately and listing the original human
                    # sponsors as primary
                    spon_re = re.compile('by ([^;(\n]+;?|\w+)')
                    sponsor = spon_re.search(hist).group(1).strip('; ')
                    bill.add_sponsor('primary', sponsor)

                    # Get co-sponsors
                    cospon_re = re.compile('\((CO-SPONSORS|CO-AUTHORS)\) ([\w .]+(;[\w .\n]+){0,})', re.MULTILINE)
                    cospon_match = cospon_re.search(hist)
                    if cospon_match:
                        for cosponsor in cospon_match.group(2).split(';'):
                            cosponsor = cosponsor.replace('\n', '').strip()
                            bill.add_sponsor('cosponsor', cosponsor)


                    self.add_bill(bill)

    def scrape_bills(self, chamber, year):
        if year not in self.metadata['session_details']:
            raise NoDataForYear(year)

        self.scrape_session(chamber, year)
        for session in self.metadata['session_details'][year]['sub_sessions']:
            self.scrape_session(chamber, session)

if __name__ == '__main__':
    FLLegislationScraper().run()
