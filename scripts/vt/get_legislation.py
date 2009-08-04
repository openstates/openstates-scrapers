#!/usr/bin/env python
import urllib2, urllib
import re
from BeautifulSoup import BeautifulSoup
import datetime as dt
import time

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import *

def parse_exec_date(date_str):
    """
    Parse dates for executive actions.
    """

    match = re.search('(\w+ \d{1,2}, \d{4,4})', date_str)
    if match:
        return dt.datetime.strptime(match.group(1), "%B %d, %Y")

    match = re.search('(\d{1,2}/\d{1,2}/\d{4,4})', date_str)
    if match:
        return dt.datetime.strptime(match.group(1), "%m/%d/%Y")

    raise ScrapeError("Invalid executive action date: %s" % date_str)

class VTLegislationScraper(LegislationScraper):

    state = 'vt'

    metadata = {
        'state_name': 'Vermont',
        'legislature_name': 'Vermont General Assembly',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Representative',
        'upper_term': 2,
        'lower_term': 2,
        'sessions': ['1987-1988', '1989-1990', '1991-1992', '1993-1994',
                     '1995-1996', '1997-1998', '1999-2000', '2001-2002',
                     '2003-2004', '2005-2006', '2007-2008', '2009-2010'],
        'session_details': {
            '1987-1988': {'years': [1987, 1988], 'sub_sessions': []},
            '1989-1990': {'years': [1989, 1990], 'sub_sessions': []},
            '1991-1992': {'years': [1991, 1992], 'sub_sessions': []},
            '1993-1994': {'years': [1993, 1994], 'sub_sessions': []},
            '1995-1996': {'years': [1995, 1996], 'sub_sessions': []},
            '1997-1998': {'years': [1997, 1998], 'sub_sessions': []},
            '1999-2000': {'years': [1999, 2000], 'sub_sessions': []},
            '2001-2002': {'years': [2001, 2003], 'sub_sessions': []},
            '2003-2004': {'years': [2003, 2004], 'sub_sessions': []},
            '2005-2006': {'years': [2005, 2006], 'sub_sessions': []},
            '2007-2008': {'years': [2007, 2008], 'sub_sessions': []},
            '2009-2010': {'years': [2009, 2010], 'sub_sessions': []},
            }
        }

    def scrape_session_new(self, chamber, session):
        if chamber == "lower":
            bill_abbr = "H."
        else:
            bill_abbr = "S."

        bill_list_url = "http://www.leg.state.vt.us/docs/bills.cfm?Session=%s&Body=%s" % (session.split('-')[1], bill_abbr[0])
        self.log("Getting bill list for %s %s" % (chamber, session))
        bill_list = BeautifulSoup(self.urlopen(bill_list_url))

        bill_link_re = re.compile('.*?Bill=%s\.\d+.*' % bill_abbr[0])
        for bill_link in bill_list.findAll('a', href=bill_link_re):
            bill_id = bill_link.string
            bill_title = bill_link.parent.findNext('b').string
            bill = Bill(session, chamber, bill_id, bill_title)

            bill_info_url = "http://www.leg.state.vt.us" + bill_link['href']
            info_page = BeautifulSoup(self.urlopen(bill_info_url))

            text_links = info_page.findAll('blockquote')[1].findAll('a')
            for text_link in text_links:
                bill.add_version(text_link.string,
                                 "http://www.leg.state.vt.us" +
                                 text_link['href'])

            act_table = info_page.findAll('blockquote')[2].table
            for row in act_table.findAll('tr')[1:]:
                action = ""
                for s in row.findAll('td')[1].findAll(text=True):
                    action += s + " "
                action = action.strip()

                match = re.search('Governor on (.*)$', action)
                if match:
                    act_date = parse_exec_date(match.group(1).strip())
                    actor = 'Governor'
                else:
                    if row['bgcolor'] == 'Salmon':
                        actor = 'lower'
                    else:
                        actor = 'upper'

                    if row.td.a:
                        act_date = row.td.a.string
                    else:
                        act_date = row.td.string

                    act_date = re.search(
                        '\d{1,2}/\d{1,2}/\d{4,4}', act_date).group(0)
                    act_date = dt.datetime.strptime(act_date, '%m/%d/%Y')

                bill.add_action(actor, action, act_date)

                vote_link = row.find('a', text='Details')
                if vote_link:
                    self.parse_vote_new(bill, actor, vote_link.parent['href'])

            sponsors = info_page.find(
                text='Sponsor(s):').parent.parent.findAll('b')
            bill.add_sponsor('primary', sponsors[0].string)
            for sponsor in sponsors[1:]:
                bill.add_sponsor('cosponsor', sponsor.string)

            self.add_bill(bill)

    def parse_vote_new(self, bill, chamber, url):
        vote_page = BeautifulSoup(self.urlopen(url))
        table = vote_page.table
        info_row = table.findAll('tr')[1]

        date = info_row.td.contents[0]
        date = dt.datetime.strptime(date, '%m/%d/%Y')
        motion = info_row.findAll('td')[1].contents[0]
        yes_count = int(info_row.findAll('td')[2].contents[0])
        no_count = int(info_row.findAll('td')[3].contents[0])
        abs_count = int(info_row.findAll('td')[4].contents[0])
        passed = info_row.findAll('td')[5].contents[0] == 'Pass'

        vote = Vote(chamber, date, motion, passed,
                    yes_count, no_count, abs_count)

        for tr in table.findAll('tr')[3:]:
            if len(tr.findAll('td')) != 2:
                continue

            name = tr.td.contents[0].split(' of')[0]
            type = tr.findAll('td')[1].contents[0]
            if type.startswith('Yea'):
                vote.yes(name)
            elif type.startswith('Nay'):
                vote.no(name)
            else:
                vote.other(name)

        bill.add_vote(vote)

    def scrape_session_old(self, chamber, session):
        if chamber == "lower":
            bill_abbr = "H."
            chamber_name = "House"
            other_chamber = "Senate"
        else:
            bill_abbr = "S."
            chamber_name = "Senate"
            other_chamber = "House"

        start_date = '1/1/%s' % session.split('-')[0]
        data = urllib.urlencode({'Date': start_date,
                                 'Body': bill_abbr[0],
                                 'Session': session.split('-')[1]})
        bill_list_url = "http://www.leg.state.vt.us/database/rintro/results.cfm"
        self.log("Getting bill list for %s %s" % (chamber, session))
        bill_list = BeautifulSoup(urllib2.urlopen(bill_list_url, data))

        bill_link_re = re.compile('.*?Bill=%s.\d+.*' % bill_abbr[0])
        for bill_link in bill_list.findAll('a', href=bill_link_re):
            bill_id = bill_link.string
            bill_title = bill_link.parent.parent.findAll('td')[1].string
            bill = Bill(session, chamber, bill_id, bill_title)

            info_page = BeautifulSoup(self.urlopen(
                    "http://www.leg.state.vt.us" + bill_link['href']))

            text_links = info_page.findAll('blockquote')[-1].findAll('a')
            for text_link in text_links:
                bill.add_version(text_link.string,
                                 "http://www.leg.state.vt.us" +
                                 text_link['href'])

            sponsors = info_page.find(
                text='Sponsor(s):').parent.findNext('td').findAll('b')
            bill.add_sponsor('primary', sponsors[0].string)
            for sponsor in sponsors[1:]:
                bill.add_sponsor('cosponsor', sponsor.string)

            # Grab actions from the originating chamber
            act_table = info_page.find(
                text='%s Status:' % chamber_name).findNext('table')
            for row in act_table.findAll('tr')[3:]:
                action = row.td.string.replace('&nbsp;', '').strip(':')

                act_date = row.findAll('td')[1].b.string.replace('&nbsp;', '')
                if act_date != "":
                    detail = row.findAll('td')[2].b
                    if detail and detail.string != "":
                        action += ": %s" % detail.string.replace('&nbsp;', '')
                    bill.add_action(chamber, action, act_date)

            # Grab actions from the other chamber
            act_table = info_page.find(
                text='%s Status:' % other_chamber).findNext('table')
            if act_table:
                if chamber == 'upper':
                    act_chamber = 'lower'
                else:
                    act_chamber = 'upper'
                for row in act_table.findAll('tr')[3:]:
                    action = row.td.string.replace('&nbsp;', '').strip(':')

                    act_date = row.findAll('td')[1].b.string.replace(
                        '&nbsp;', '')
                    if act_date != "":
                        detail = row.findAll('td')[2].b
                        if detail and detail.string != "":
                            action += ": %s" % detail.string.replace(
                                '&nbsp;', '')
                        date = dt.datetime.strptime(act_date, '%m/%d/%Y')
                        bill.add_action(act_chamber, action, act_date)

            self.add_bill(bill)

    def scrape_bills(self, chamber, year):
        session = "%s-%d" % (year, int(year) + 1)
        if session not in self.metadata['session_details']:
            raise NoDataForYear(year)

        if int(year) >= 2009:
            self.scrape_session_new(chamber, session)
        else:
            self.scrape_session_old(chamber, session)

    def scrape_legislators(self, chamber, year):
        if int(year) != 2009:
            return
        session = "%s-%d" % (year, int(year) + 1)

        # What Vermont claims are Word and Excel files are actually
        # just HTML tables
        # What Vermont claims is a CSV file is actually one row of comma
        # separated values followed by a ColdFusion error.
        leg_url = "http://www.leg.state.vt.us/legdir/memberdata.cfm/memberdata.doc?FileType=W"
        leg_table = BeautifulSoup(self.urlopen(leg_url))

        for tr in leg_table.findAll('tr')[1:]:
            leg_cham = tr.findAll('td')[3].contents[0]
            if leg_cham == 'H' and chamber == 'upper':
                continue
            if leg_cham == 'S' and chamber == 'lower':
                continue

            district = tr.findAll('td')[5].contents[0]
            district = district.replace(' District', '').strip()
            first = tr.findAll('td')[6].contents[0]

            middle = tr.findAll('td')[7]
            if len(middle.contents) == 0:
                middle = ''
            else:
                middle = middle.contents[0].strip()

            last = tr.findAll('td')[8].contents[0]

            if len(middle) == 0:
                full = "%s, %s" % (last, first)
            else:
                full = "%s, %s %s." % (last, first, middle)

            official_email = tr.findAll('td')[9]
            if len(official_email.contents) == 0:
                official_email = ''
            else:
                official_email = official_email.contents[0]

            party = tr.findAll('td')[4].contents[0]
            if party == 'D':
                party = 'Democrat'
            elif party == 'R':
                party = 'Republican'
            elif party == 'I':
                party = 'Independent'
            elif party == 'P':
                party = 'Progressive'

            leg = Legislator(session, chamber, district, full,
                             first, last, middle, party,
                             official_email=official_email)
            self.add_legislator(leg)

if __name__ == '__main__':
    VTLegislationScraper().run()
