#!/usr/bin/env python
import urllib2
import re
import datetime as dt
import html5lib

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import *

class SDLegislationScraper(LegislationScraper):

    state = 'sd'
    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

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
            '1997': {'years': [1997], 'sub_sessions': ['1997s'],
                     'alternate': '72nd'},
            '1998': {'years': [1998], 'sub_sessions': [], 'alternate': '73rd'},
            '1999': {'years': [1999], 'sub_sessions': [], 'alternate': '74th'},
            '2000': {'years': [2000], 'sub_sessions': ['2000s'],
                     'alternate': '75th'},
            '2001': {'years': [2001], 'sub_sessions': ['2001s'],
                     'alternate': '76th'},
            '2002': {'years': [2002], 'sub_sessions': [], 'alternate': '77th'},
            '2003': {'years': [2003], 'sub_sessions': ['2003s'],
                     'alternate': '78th'},
            '2004': {'years': [2004], 'sub_sessions': [], 'alternate': '79th'},
            '2005': {'years': [2005], 'sub_sessions': ['2005s'],
                     'alternate': '80th'},
            '2006': {'years': [2006], 'sub_sessions': [], 'alternate': '81st'},
            '2007': {'years': [2007], 'sub_sessions': [], 'alternate': '82nd'},
            '2008': {'years': [2008], 'sub_sessions': [], 'alternate': '83rd'},
            '2009': {'years': [2009], 'sub_sessions': [], 'alternate': '84th'},
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
        bill_list = self.soup_parser(self.urlopen(bill_list_url))

        # Format of bill link contents
        bill_re = re.compile(u'%s\xa0(\d+)' % bill_abbr)
        date_re = re.compile('\d{2}/\d{2}/\d{4}')

        for bill_link in bill_list.findAll('a'):
            if len(bill_link.contents) == 0:
                # Empty link
                continue

            #print bill_link.contents[0]
            bill_match = bill_re.search(bill_link.contents[0])
            if not bill_match:
                continue

            # Parse bill ID and name
            bill_id = bill_link.contents[0].replace(u'\xa0', ' ')
            bill_name = bill_link.findNext().contents[0]

            # Download history page
            hist_url = session_url + bill_link['href']
            history = self.soup_parser(self.urlopen(hist_url))

            bill = Bill(session, chamber, bill_id, bill_name)

            # Get all bill versions
            text_table = history.findAll('table')[1]
            for row in text_table.findAll('tr')[2:]:
                #version_date = row.find('td').string
                version_path = row.findAll('td')[1].a['href']
                version_url = "http://legis.state.sd.us/sessions/%s/%s" % (
                    session, version_path)

                version_name = row.findAll('td')[1].a.contents[0].strip()

                bill.add_version(version_name, version_url)

            # Get actions
            act_table = history.find('table')
            for act_row in act_table.findAll('tr')[6:]:
                if act_row.find(text='Action'):
                    continue

                # Get the date (if can't find one then this isn't an action)
                date_match = date_re.match(act_row.td.a.contents[0])
                if not date_match:
                    continue
                act_date = date_match.group(0)

                # Get the action string
                action = ""
                for node in act_row.findAll('td')[1].contents:
                    if hasattr(node, 'contents'):
                        action += node.contents[0]

                        if node.contents[0].startswith('YEAS'):
                            # This is a vote!
                            vote_url = "http://legis.state.sd.us/sessions/%s/%s" % (session, node['href'])
                            vote = self.scrape_new_vote(vote_url)
                            vote['date'] = act_date
                            bill.add_vote(vote)
                    else:
                        action += node
                action = action.strip()

                # Add action
                bill.add_action(chamber, action, act_date)

            self.add_bill(bill)

    def scrape_new_vote(self, url):
        vote_page = self.soup_parser(self.urlopen(url))

        header = vote_page.find(id="ctl00_contentMain_hdVote").contents[0]

        chamber_name = header.split(', ')[1]
        if chamber_name.startswith('House'):
            chamber = 'lower'
        else:
            chamber = 'upper'

        location = ' '.join(chamber_name.split(' ')[1:])
        if location.startswith('of Representatives'):
            location = ''

        motion = ', '.join(header.split(', ')[2:])

        yes_count = int(vote_page.find(
            id="ctl00_contentMain_tdAyes").contents[0])
        no_count = int(vote_page.find(
            id="ctl00_contentMain_tdNays").contents[0])
        excused_count = int(vote_page.find(
            id="ctl00_contentMain_tdExcused").contents[0])
        absent_count = int(vote_page.find(
            id="ctl00_contentMain_tdAbsent").contents[0])
        other_count = excused_count + absent_count

        passed = yes_count > no_count

        vote = Vote(chamber, None, motion, passed,
                    yes_count, no_count,
                    other_count, excused_count=excused_count,
                    absent_count=absent_count,
                    location=location)

        vote_tbl = vote_page.find(id="ctl00_contentMain_tblVotes")
        for row in vote_tbl.findAll('tr'):
            for td in vote_tbl.findAll('td'):
                if td.contents[0] == 'Yea':
                    vote.yes(td.findPrevious().contents[0])
                elif td.contents[0] == 'Nay':
                    vote.no(td.findPrevious().contents[0])
                elif td.contents[0] in ['Excused', 'Absent']:
                    vote.other(td.findPrevious().contents[0])

        return vote

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
        #bill_list_raw = self.urlopen(bill_list_url)
        #bill_list_raw = bill_list_raw.replace('BORDER= ', '').replace('"</A>', '"></A>')
        bill_list = self.soup_parser(self.urlopen(bill_list_url))

        # Bill and text link formats
        bill_re = re.compile('%s (\d+)' % bill_abbr)
        text_re = re.compile('/sessions/%s/bills/%s.*\.htm' % (session, bill_abbr), re.IGNORECASE)
        date_re = re.compile('\d{2}/\d{2}/\d{4}')

        for bill_link in bill_list.findAll('a', href=re.compile('\d\.htm$')):
            if len(bill_link.contents) == 0:
                # Empty link
                continue

            bill_match = bill_re.match(bill_link.contents[0])
            if not bill_match:
                # Not bill link
                continue

            # Get the bill ID and name
            bill_id = bill_link.contents[0]
            bill_name = bill_link.findNext().contents[0]

            # Get history page (replacing malformed tag)
            hist_url = session_url + bill_link['href']
            #history_raw = self.urlopen(hist_url)
            #history_raw = history_raw.replace('BORDER=>', '>')
            history = self.soup_parser(self.urlopen(hist_url))

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

                version_name = row.findAll('td')[1].a.contents[0].strip()

                bill.add_version(version_name, version_url)

            # Get actions
            act_table = history.find('table')
            for act_row in act_table.findAll('tr')[6:]:
                if act_row.find(text="Action"):
                    continue

                # Get the date (if can't find one then this isn't an action)
                date_match = date_re.match(act_row.td.a.contents[0])
                if not date_match:
                    continue
                act_date = date_match.group(0)

                # Get the action string
                action = ""
                for node in act_row.findAll('td')[1].contents:
                    if hasattr(node, 'contents'):
                        action += node.contents[0]

                        if node.contents[0].startswith('YEAS'):
                            # This is a vote!
                            if node['href'][0] == '/':
                                vote_url = "http://legis.state.sd.us/%s" % (
                                    node['href'])
                            else:
                                vote_url = "http://legis.state.sd.us/sessions/%s/%s" % (session, node['href'])
                            vote = self.scrape_old_vote(vote_url)
                            vote['date'] = act_date
                            bill.add_vote(vote)
                    else:
                        action += node
                action = action.strip()

                # Add action
                bill.add_action(chamber, action, act_date)

            self.add_bill(bill)

    def scrape_old_vote(self, url):
        vote_page = self.soup_parser(self.urlopen(url))

        header = vote_page.h3.contents[0]

        chamber_name = header.split(', ')[1]
        if chamber_name.startswith('House'):
            chamber = 'lower'
        else:
            chamber = 'upper'

        location = ' '.join(chamber_name.split(' ')[1:])
        if location.startswith('of Representatives'):
            location = ''

        motion = ', '.join(header.split(', ')[2:])

        def get_count(cell):
            if len(cell.contents) == 0:
                return 0
            else:
                return int(cell.contents[0])

        results_tbl = vote_page.findAll('table')[1]
        yes_count = get_count(results_tbl.findAll('td')[1])
        no_count = get_count(results_tbl.findAll('td')[3])
        excused_count = get_count(results_tbl.findAll('td')[5])
        absent_count = get_count(results_tbl.findAll('td')[7])
        other_count = excused_count + absent_count

        passed = yes_count > no_count

        vote = Vote(chamber, None, motion, passed,
                    yes_count, no_count,
                    other_count, excused_count=excused_count,
                    absent_count=absent_count,
                    location=location)

        vote_tbl = vote_page.table
        for row in vote_tbl.findAll('tr'):
            for td in vote_tbl.findAll('td'):
                if td.contents[0] == 'Yea':
                    vote.yes(td.findPrevious().contents[0])
                elif td.contents[0] == 'Nay':
                    vote.no(td.findPrevious().contents[0])
                elif td.contents[0] in ['Excused', 'Absent']:
                    vote.other(td.findPrevious().contents[0])

        return vote

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

    def scrape_new_legislators(self, chamber, session):
        """
        Scrape legislators from 2009 and later.
        """

        if chamber == 'upper':
            search = 'Senate Members'
        else:
            search = 'House Members'

        leg_url = "http://legis.state.sd.us/sessions/%s/MemberMenu.aspx" % (
            session)
        leg_list = self.soup_parser(self.urlopen(leg_url))

        list_div = leg_list.find(text=search).findNext('div')

        for link in list_div.findAll('a'):
            full_name = link.contents[0].strip()
            first_name = full_name.split(', ')[1].split(' ')[0]
            last_name = full_name.split(',')[0]
            middle_name = ''

            leg_page_url = "http://legis.state.sd.us/sessions/%s/%s" % (
                session, link['href'])
            leg_page = self.soup_parser(self.urlopen(leg_page_url))

            party = leg_page.find(
                id="ctl00_contentMain_spanParty").contents[0].strip()

            district = leg_page.find(
                id="ctl00_contentMain_spanDistrict").contents[0].strip()

            occ_span = leg_page.find(id="ctl00_contentMain_spanOccupation")
            if len(occ_span.contents) > 0:
                occupation = occ_span.contents[0].strip()
            else:
                occupation = None

            legislator = Legislator(session, chamber, district,
                                    full_name, first_name, last_name,
                                    middle_name, party=party,
                                    occupation=occupation)
            self.add_legislator(legislator)

    def scrape_old_legislators(self, chamber, session):
        """
        Scrape pre-2009 legislators.
        """
        if chamber == 'upper':
            chamber_name = 'Senate'
        else:
            chamber_name = 'House'

        if int(session) < 2008:
            filename = 'district.htm'
        else:
            filename = 'MembersDistrict.htm'

        leg_list_url = "http://legis.state.sd.us/sessions/%s/%s" % (
            session, filename)
        leg_list = self.soup_parser(self.urlopen(leg_list_url))

        for district_str in leg_list.findAll('h2'):
            district = district_str.contents[0].split(' ')[1].lstrip('0')

            for row in district_str.findNext('table').findAll('tr')[1:]:
                if row.findAll('td')[1].contents[0].strip() != chamber_name:
                    continue

                full_name = row.td.a.contents[0].strip()
                first_name = full_name.split(', ')[1].split(' ')[0]
                last_name = full_name.split(',')[0]
                middle_name = ''

                party = row.findAll('td')[3].contents[0].strip()
                occupation = row.findAll('td')[4].contents[0].strip()

                legislator = Legislator(session, chamber, district,
                                        full_name, first_name, last_name,
                                        middle_name, party=party,
                                        occupation=occupation)
                self.add_legislator(legislator)

    def scrape_legislators(self, chamber, year):
        if year not in self.metadata['session_details']:
            raise NoDataForYear(year)

        if int(year) >= 2009:
            self.scrape_new_legislators(chamber, year)
        else:
            self.scrape_old_legislators(chamber, year)
        
if __name__ == '__main__':
    SDLegislationScraper().run()
