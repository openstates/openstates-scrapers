#!/usr/bin/env python
from __future__ import with_statement
import html5lib
import datetime as dt
import re

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import LegislationScraper, Legislator, Bill

def clean_legislators(s):
    s = s.replace('&nbsp;', ' ').strip()
    return [l.strip() for l in s.split(';') if l]

def split_name(full_name):
    m = re.match('(\w+) (\w)\. (\w+)', full_name)
    if m:
        first_name = m.group(1)
        middle_name = m.group(2)
        last_name = m.group(3)
    else:
        first_name = full_name.split(' ')[0]
        last_name = ' '.join(full_name.split(' ')[1:])
        middle_name = ''

    suffix = ''
    if last_name.endswith(', Jr.'):
        last_name = last_name.replace(', Jr.', '')
        suffix = 'Jr.'

    return (first_name, last_name, middle_name, suffix)

class NCLegislationScraper(LegislationScraper):

    state = 'nc'
    soup_parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    metadata = {
        'state_name': 'North Carolina',
        'legislature_name': 'The North Carolina General Assembly',
        'lower_chamber_name': 'House of Representatives',
        'upper_chamber_name': 'Senate',
        'lower_title': 'Representative',
        'upper_title': 'Senator',
        'lower_term': 2,
        'upper_term': 2,
        'sessions': ['1985-1986', '1987-1988', '1989-1990', '1991-1992',
                     '1993-1994', '1995-1996', '1997-1998', '1999-2000',
                     '2001-2002', '2003-2004', '2005-2006', '2007-2008',
                     '2009-2010'],
        'session_details': {
             '1985-1986': {'years': ['1985', '1986'],
                           'sub_sessions': ['1985E1']},
             '1987-1988': {'years': [1987, 1988],
                           'sub_sessions': []},
             '1989-1990': {'years': [1989, 1990],
                           'sub_sessions': ['1989E1', '1989E2'],},
             '1991-1992': {'years': [1991, 1992],
                          'sub_sessions': ['1991E1']},
             '1993-1994': {'years': [1993, 1994],
                           'sub_sessions': ['1993E1']},
             '1995-1996': {'years': [1995, 1996],
                           'sub_sessions': ['1995E1', '1995E2']},
             '1997-1998': {'years': [1997, 1998],
                           'sub_sessions': ['1997E1']},
             '1999-2000': {'years': [1999, 2000],
                           'sub_sessions': ['1999E1', '1999E2']},
             '2001-2002': {'years': [2001, 2002],
                           'sub_sessions': ['2001E1']},
             '2003-2004': {'years': [2003, 2004],
                           'sub_sessions': ['2003E1', '2003E2', '2003E3']},
             '2005-2006': {'years': [2005, 2006],
                           'sub_sessions': []},
             '2007-2008': {'years': [2007, 2008],
                           'sub_sessions': ['2007E1', '2007E2']},
             '2009-2010': {'years': [2009, 2010],
                           'sub_sessions': []},
             }}

    def get_bill_info(self, session, sub, bill_id):
        bill_detail_url = 'http://www.ncga.state.nc.us/gascripts/BillLookUp/BillLookUp.pl?bPrintable=true&Session=%s&BillID=%s&votesToView=all' % (session[0:4] + sub, bill_id)
        # parse the bill data page, finding the latest html text
        if bill_id[0] == 'H':
            chamber = 'lower'
        else:
            chamber = 'upper'

        bill_data = self.urlopen(bill_detail_url)
        bill_soup = self.soup_parser(bill_data)

        bill_title = bill_soup.findAll('div', style="text-align: center; font: bold 20px Arial; margin-top: 15px; margin-bottom: 8px;")[0].contents[0]

        bill = Bill(session + sub, chamber, bill_id, bill_title)
        bill.add_source(bill_detail_url)

        # get all versions
        links = bill_soup.findAll('a', href=re.compile('/Sessions/%s/Bills/\w+/HTML' % session[0:4]))
        for link in links:
            version_name = link.parent.previousSibling.previousSibling.contents[0].replace('&nbsp;', ' ')
            version_url = 'http://www.ncga.state.nc.us' + link['href']
            bill.add_version(version_name, version_url)

        # figure out which table has sponsor data
        sponsor_table = bill_soup.findAll('th', text='Sponsors', limit=1)[0].findParents('table', limit=1)[0]
        sponsor_rows = sponsor_table.findAll('tr')
        for leg in sponsor_rows[1].td.findAll('a'):
            bill.add_sponsor('primary',
                             leg.contents[0].replace(u'\u00a0', ' '))
        for leg in sponsor_rows[2].td.findAll('a'):
            bill.add_sponsor('cosponsor',
                             leg.contents[0].replace(u'\u00a0', ' '))


        action_table = bill_soup.findAll('th', text='Chamber', limit=1)[0].findParents('table', limit=1)[0]
        for row in action_table.findAll('tr'):
            cells = row.findAll('td')
            if len(cells) != 3: continue
            act_date,actor,action = map(lambda x: self.flatten(x), cells)
            act_date = dt.datetime.strptime(act_date, '%m/%d/%Y')

            if actor == 'Senate': actor = 'upper'
            elif actor == 'House': actor = 'lower'
            elif action.endswith('Gov.'): actor = 'Governor'
            bill.add_action(actor, action, act_date)


        # http://www.ncga.state.nc.us/gascripts/voteHistory/RollCallVoteTranscriptP.pl?bPrintable=true&sSession=2009&sChamber=H&RCS=1
        # /gascripts/voteHistory/RollCallVoteTranscript.pl?sSession=2009&sChamber=H&RCS=1
        for vote in bill_soup.findAll('a', href=re.compile('RollCallVoteTranscript')):
            self.get_vote(bill, vote['href'])



        self.add_bill(bill)

    def get_vote(self, bill, url):
        url = 'http://www.ncga.state.nc.us' + url
        data = self.urlopen(url)
        soup = self.soup_parser(data)


    def scrape_session(self, chamber, session, sub):
        url = 'http://www.ncga.state.nc.us/gascripts/SimpleBillInquiry/displaybills.pl?Session=%s&tab=Chamber&Chamber=%s' % (session[0:4] + sub, chamber)

        data = self.urlopen(url)
        soup = self.soup_parser(data)

        for row in soup.findAll('table')[6].findAll('tr')[1:]:
            td = row.find('td')
            bill_id = td.a.contents[0]
            self.get_bill_info(session, sub, bill_id)

    def scrape_bills(self, chamber, year):
        chamber = {'lower':'House', 'upper':'Senate'}[chamber]

        if int(year) % 2 != 1:
            raise NoDataForYear(year)

        session = "%d-%d" % (int(year), int(year) + 1)

        self.scrape_session(chamber, session, '')
        for sub in self.metadata['session_details'][session]['sub_sessions']:
            self.scrape_session(chamber, session, sub[4:])

    def scrape_legislators(self, chamber, year):
        if year != '2009':
            raise NoDataForYear(year)

        session = "%d-%d" % (int(year), int(year) + 1)

        url = "http://www.ncga.state.nc.us/gascripts/members/memberList.pl?sChamber="
        if chamber == 'lower':
            url += 'House'
        else:
            url += 'Senate'

        with self.urlopen_context(url) as leg_list_data:
            leg_list = self.soup_parser(leg_list_data)
            leg_table = leg_list.find('div', id='mainBody').find('table')

            for row in leg_table.findAll('tr')[1:]:
                party = row.td.contents[0].strip()
                if party == 'Dem':
                    party = 'Democrat'
                elif party == 'Rep':
                    party = 'Republican'

                district = row.findAll('td')[1].contents[0].strip()
                full_name = row.findAll('td')[2].a.contents[0].strip()
                full_name = full_name.replace(u'\u00a0', ' ')
                (first_name, last_name, middle_name, suffix) = split_name(full_name)

                legislator = Legislator(session, chamber, district, full_name,
                                        first_name, last_name, middle_name,
                                        party, suffix=suffix)
                legislator.add_source(url)
                self.add_legislator(legislator)

    def flatten(self, tree):
        def squish(tree):
            if tree.string:
                s = tree.string
            else:
                s = map(lambda x: self.flatten(x), tree.contents)
            if len(s) == 1:
                s = s[0]
            return s
        return ''.join(squish(tree)).strip()

if __name__ == '__main__':
    NCLegislationScraper.run()
