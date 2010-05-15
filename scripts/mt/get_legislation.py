#!/usr/bin/env python
# -*- coding: latin-1 -*-

from datetime import datetime
import csv
import html5lib
import os
import re
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import LegislationScraper, NoDataForYear, Legislator



class MTScraper(LegislationScraper):
    #must set state attribute as the state's abbreviated name
    state = 'mt'

    def __init__(self, *args, **kwargs):
        super(MTScraper, self).__init__(*args, **kwargs)
        self.parser = html5lib.HTMLParser(tree = html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

        self.metadata = {
            'state_name': 'Montana',
            'legislature_name': 'Montana Legislature',
            'upper_chamber_name': 'Senate',
            'lower_chamber_name': 'House of Representatives',
            'upper_title': 'Senator',
            'lower_title': 'Representative',
            'upper_term': 4,
            'lower_term': 2,
            'sessions': ['55th', '56th', '57th', '58th', '59th', '60th', '61st'],
            'session_details': {
                '55th': {'years': [1997, 1998], 'sub_sessions': []},
                '56th': {'years': [1999, 2000],
                         'sub_sessions': ['1999 Special Session', '2000 Special Legislative']},
                '57th': {'years': [2001, 2002],
                         'sub_sessions': ['August 2002 Special Session #1', 'August 2002 Special Session #2']},
                '58th': {'years': [2003, 2004], 'sub_sessions': []},
                '59th': {'years': [2005, 2006], 'sub_sessions': ['December 2005 Special Session']},
                '60th': {'years': [2007, 2008],
                         'sub_sessions': ['2007 September Special Session #1', '2007 September Special Session #2']},
                '61st': {'years': [2009, 2010], 'sub_sessions': []},
                }
            }

        self.base_year = 1999
        self.base_session = 56

    def getSession(self, year):
        for session, years in self.metadata['session_details'].items():
            if year in years['years']:
                return session

    def get_suffix(self, year):
        if str(year)[-2:] in ('11', '12', '13'):
            return 'th'
        last_number = str(year)[-1:]
        if last_number in ('0', '4', '5', '6', '7', '8', '9'):
            return 'th'
        elif last_number in ('1'):
            return 'st'
        elif last_number in ('2'):
            return 'nd'
        elif last_number in ('3'):
            return 'rd'


    def scrape_legislators(self, chamber, year):
        year = int(year)
        #2 year terms starting on odd year, so if even number, use the previous odd year
        if year < self.base_year:
            raise NoDataForYear(year)
        if year % 2 == 0:
            year -= 1


        session = self.base_session + ((year - self.base_year) / 2)
        suffix = self.get_suffix(session)
        if year < 2003:
            self.scrape_pre_2003_legislators(chamber, year, session, suffix)
        else:
            self.scrape_post_2003_legislators(chamber, year, session, suffix)

    def scrape_pre_2003_legislators(self, chamber, year, session, suffix):
        url = 'http://leg.mt.gov/css/Sessions/%d%s/legname.asp' % (session, suffix)
        page_data = self.parser(self.urlopen(url))
        if year == 2001:
            if chamber == 'upper':
                tableName = '57th Legislatore Roster Senate (2001-2002)'
                startRow = 3
            else:
                tableName = '57th Legislator Roster (House)(2001-2002)'
                startRow = 5
        elif year == 1999:
            if chamber == 'upper':
                tableName = 'Members of the Senate'
                startRow = 3
            else:
                tableName = 'Members of the House'
                startRow = 5
        for row in page_data.find('table', attrs = {'name' : tableName}).findAll('tr')[startRow:]:
            row = row.findAll('td')
            #Ignore row with just email in it
            if str(row[0].contents[0]).strip() == '&nbsp;':
                continue
            #Parse different locations for name if name is a link
            if row[0].find('a'):
                name = row[0].contents[0].next
                #print name.next
                party_letter = name.next[2]
            else:
                if chamber == 'upper' and year == 2001:
                    name, party_letter = row[0].contents[2].rsplit(' (', 1)
                else:
                    name, party_letter = row[0].contents[0].rsplit(' (', 1)
                party_letter = party_letter[0]

            #Get first name, last name, and suffix out of name string
            nameParts = [namePart.strip() for namePart in name.split(',')]
            assert len(nameParts) < 4
            if len(nameParts) == 2:
                #Case last_name, first_name
                last_name, first_name = nameParts
            elif len(nameParts) == 3:
                #Case last_name, suffix, first_name
                last_name = ' '.join(nameParts[0:2])
                first_name = nameParts[2]

            district = row[2].contents[0].strip()

            if party_letter == 'R':
                party = 'Republican'
            elif party_letter == 'D':
                party = 'Democrat'
            else:
                #Haven't yet run into others, so not sure how the state abbreviates them
                party = party_letter

            legislator = Legislator(session, chamber, district, '%s %s' % (first_name, last_name), \
                                    first_name, last_name, '', party)
            legislator.add_source(url)
            self.save_legislator(legislator)

    def scrape_post_2003_legislators(self, chamber, year, session, suffix):
        url = 'http://leg.mt.gov/content/sessions/%d%s/%d%sMembers.txt' % \
            (session, suffix, year, chamber == 'upper' and 'Senate' or 'House')

        #Currently 2009 is different
        if year > 2008:
            csv_parser = csv.reader(self.urlopen(url).split(os.linesep), delimiter = '\t')
            #Discard title row
            csv_parser.next()
        else:
            csv_parser = csv.reader(self.urlopen(url).split(os.linesep))

        for entry in csv_parser:
            if not entry:
                continue
            if year == 2003:
                first_name, last_name = entry[0].split(' ', 2)[1:3]
                party_letter = entry[1]
                district = entry[2]
            else:
                last_name = entry[0]
                first_name = entry[1]
                party_letter = entry[2]
                district = entry[3]#.split('D ')[1]
            if party_letter == '(R)':
                party = 'Republican'
            elif party_letter == '(D)':
                party = 'Democrat'
            else:
                party = party_letter
            first_name = first_name.capitalize()
            last_name = last_name.capitalize()
            #All we care about is the number
            district = district.split('D ')[1]

            legislator = Legislator(session, chamber, district, '%s %s' % (first_name, last_name), \
                                    first_name, last_name, '', party)
            legislator.add_source(url)
            self.save_legislator(legislator)

    def scrape_bills(self, chamber, year):
        #bill id
        #session
        #chamber
        #title
        #sponsers(name, type)
        #actions(date, actor, action)
        #votes(chamber, date, motion, passed, yes_count, no_count, other_count, yes_votes(name), no_votes(name), other_votes(name)
        if chamber == 'upper':
            return
        year = int(year)
        session = self.getSession(year)
        #2 year terms starting on odd year, so if even number, use the previous odd year
        if year < 2001:
            raise NoDataForYear(year)
        if year % 2 == 0:
            year -= 1



        base_bill_url = 'http://data.opi.mt.gov/bills/%d/BillHtml/' % year
        #Get all links, exclude 1st because it is "To Parent Directory"
        url_list = (link.contents[0] for link in self.parser(self.urlopen(base_bill_url)).findAll('a')[1:])
        for bill_url in url_list:
            anchors = self.parser(self.urlopen(base_bill_url + bill_url)).findAll('a')
            for anchor in anchors:
                if anchor.contents:
                    if anchor.contents[0].next.next == 'status of this bill':
                        #Open link to status page
                        status_url = anchor['href'].replace('\n', '')
                        status_page = self.parser(self.urlopen(status_url))
                        bill_id = status_page.find(text = 'Bill Type - Number:').next.contents[0]
                        title = status_page.find(text = 'Short Title:').next.contents[0]
                        #Discard first row as it is the 'title' row
                        sponsors = []
                        for sponsor_row in status_page.find('a', attrs = {'name' : 'spon_table'}).table.findAll('tr')[1:]:
                            sponsor_columns = sponsor_row.findAll('td')
                            sponsor_type = sponsor_columns[0].contents[0]
                            sponsor_last_name = sponsor_columns[1].contents[0]
                            sponsor_first_name = sponsor_columns[2].contents[0]
                            sponsor_middle_initial = sponsor_columns[3].contents[0]
                            nbsp = '\xA0'
                            sponsor_first_name = '' if sponsor_first_name == nbsp else ', ' + sponsor_first_name
                            #sponsor_middle_initial = sponsor_middle_initial == nbsp and '' or ' %s.' % sponsor_middle_initial
                            sponsor_middle_initial = '' if sponsor_middle_initial == nbsp else ' %s.' % sponsor_middle_initial
                            sponsor_full_name = sponsor_last_name + sponsor_first_name + sponsor_middle_initial
                            sponsors.append({'name' : sponsor_full_name,
                                             'type' : sponsor_type})
                        for action_row in status_page.find('a', attrs = {'name' : 'ba_table'}).table.findAll('tr')[1:]:
                            action_columns = action_row.findAll('td')
                            print action_columns
                            action_action = action_columns[0].contents[0]
                            action_actor = action_action[0:3]
                            if action_actor == "(H)":
                                action_actor = "lower"
                                action_action = action_action[4:]
                            elif action_actor == "(S)":
                                action_actor = "upper"
                                action_action = action_action[4:]
                            elif action_action == "(C)":
                                action_actor = "clerk"
                                action_action = action_action[4:]
                            else:
                                action_actor = None
                            print action_columns[1].contents[0]
                            action_date = datetime.strptime(action_columns[1].contents[0], '%m/%d/%Y')
                            action_votes_yes = action_columns[2].contents[0]
                            action_votes_no = action_columns[3].contents[0]
                            action_committee = action_columns[4].contents[0]
                            print action_action
                            print action_actor
                            print action_date
                            print action_votes_yes
                            print action_votes_no
                            print action_committee
                            break

                        print bill_id
                        print session
                        print chamber
                        print title
                        print sponsors
                        break
            if bill_url.startswith('HB'):
                all_prefix = 'HB'
                if int(bill_url[2:6]) < 100:
                    all_suffix = '0099'
            all_versions_url = 'http://data.opi.mt.gov/bills/%d/%s%s/' % (year, all_prefix, all_suffix)
            all_versions_page = self.parser(self.urlopen(all_versions_url))
            for anchor in all_versions_page.findAll('a'):
                file_name = anchor.contents[0]
                if file_name.startswith(bill_url[0:6]):
                    version_number = file_name[7]
                    if version_number == 'x':
                        version_title = 'Final Version'
                        version_url = base_bill_url + bill_url
                    else:
                        version_title = 'Version %s' % version_number
                        version_url = all_versions_url + file_name
                    print version_title
                    print version_url
            break

if __name__ == '__main__':
    MTScraper().run()
