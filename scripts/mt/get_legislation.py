#!/usr/bin/env python
# -*- coding: latin-1 -*-

from datetime import datetime
import csv
import html5lib
import os
import re
import sys
from lxml.etree import ElementTree
import lxml.html
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import Bill, LegislationScraper, NoDataForYear, Legislator, Vote


actor_map = {
    '(S)': 'upper',
    '(H)': 'lower',
    '(C)': 'clerk',
    }

sponsor_map = {
    'Primary Sponsor': 'primary'
    }

vote_passage_indicators = ['Adopted',
                           'Appointed',
                           'Carried',
                           'Concurred',
                           'Passed',
                           'Rereferred to Committee']
vote_failure_indicators = ['Failed',
                           'Rejected',
                           ]
vote_ambiguious_indicators = [
    'Indefinitely Postponed',
    'On Motion Rules Suspended',
    'Pass Consideration',
    'Reconsidered Previous',
    'Rules Suspended',
    'Segregated from Committee',
    'Special Action',
    'Sponsor List Modified',
    'Taken from']

class MTScraper(LegislationScraper):
    #must set state attribute as the state's abbreviated name
    state = 'mt'

    def __init__(self, *args, **kwargs):
        super(MTScraper, self).__init__(*args, **kwargs)
        self.parser = html5lib.HTMLParser(tree = html5lib.treebuilders.getTreeBuilder('lxml')).parse

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
        self.search_url_template = "http://laws.leg.mt.gov/laws%s/LAW0203W$BSRV.ActionQuery?P_BLTP_BILL_TYP_CD=%s&P_BILL_NO=%s&P_BILL_DFT_NO=&Z_ACTION=Find&P_SBJ_DESCR=&P_SBJT_SBJ_CD=&P_LST_NM1=&P_ENTY_ID_SEQ="

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
        year = int(year)
        session = self.getSession(year)
        #2 year terms starting on odd year, so if even number, use the previous odd year
        if year < 2001:
            raise NoDataForYear(year)
        if year % 2 == 0:
            year -= 1

        base_bill_url = 'http://data.opi.mt.gov/bills/%d/BillHtml/' % year
        index_page = ElementTree(lxml.html.fromstring(self.urlopen(base_bill_url)))

        bill_urls = []
        for bill_anchor in index_page.findall('//a'):
            # House bills start with H, Senate bills start with S
            if chamber == 'lower' and bill_anchor.text.startswith('H'):
                bill_urls.append("%s%s" % (base_bill_url, bill_anchor.text))
            elif chamber == 'upper' and bill_anchor.text.startswith('S'):
                bill_urls.append("%s%s" % (base_bill_url, bill_anchor.text))

        for bill_url in bill_urls:
            bill = self.parse_bill(bill_url, session, chamber)
            self.save_bill(bill)

    def parse_bill(self, bill_url, session, chamber):
        bill = None
        bill_page = ElementTree(lxml.html.fromstring(self.urlopen(bill_url)))
        for anchor in bill_page.findall('//a'):
            if (anchor.text_content().startswith('status of') or
                anchor.text_content().startswith('Detailed Information (status)')):
                status_url = anchor.attrib['href'].replace("\r", "").replace("\n", "")
                bill = self.parse_bill_status_page(status_url, bill_url, session, chamber)
            elif anchor.text_content().startswith('This bill in WP'):
                index_url = anchor.attrib['href']
                index_url = index_url[0:index_url.rindex('/')]
                self.add_bill_versions(bill, index_url)

        if bill is None:
            # No bill was found.  Maybe something like HB0790 in the 2005 session?
            # We can search for the bill metadata.
            page_name = bill_url.split("/")[-1].split(".")[0]
            bill_type = page_name[0:2]
            bill_number = page_name[2:]
            laws_year = bill_url.split("/")[4][2:]

            status_url = self.search_url_template % (laws_year, bill_type, bill_number)
            bill = self.parse_bill_status_page(status_url, bill_url, session, chamber)
        return bill

    def parse_bill_status_page(self, status_url, bill_url, session, chamber):
        status_page = ElementTree(lxml.html.fromstring(self.urlopen(status_url)))
        # see 2007 HB 2... weird.  
        try:
            bill_id = status_page.xpath("/div/form[1]/table[2]/tr[2]/td[2]")[0].text_content()
        except IndexError:
            bill_id = status_page.xpath('/html/html[2]/tr[1]/td[2]')[0].text_content()
        
        try:
            title = status_page.xpath("/div/form[1]/table[2]/tr[3]/td[2]")[0].text_content()
        except IndexError:
            title = status_page.xpath('/html/html[3]/tr[1]/td[2]')[0].text_content()
                
        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(bill_url)
        
        self.add_sponsors(bill, status_page)
        self.add_actions(bill, status_page)

        return bill
        

    def add_actions(self, bill, status_page):
        for action in status_page.xpath('/div/form[3]/table[1]/tr')[1:]:
            try:
                actor = actor_map[action.xpath("td[1]")[0].text_content().split(" ")[0]]
                action_name = action.xpath("td[1]")[0].text_content().replace(actor, "")[4:].strip()
            except KeyError:
                actor = ''
                action_name = action.xpath("td[1]")[0].text_content().strip()
                
            action_date = datetime.strptime(action.xpath("td[2]")[0].text, '%m/%d/%Y')
            action_votes_yes = action.xpath("td[3]")[0].text_content().replace("&nbsp", "")
            action_votes_no = action.xpath("td[4]")[0].text_content().replace("&nbsp", "")
            action_committee = action.xpath("td[5]")[0].text.replace("&nbsp", "")
            
            bill.add_action(actor, action_name, action_date)

            # TODO: Review... should something be both an action and a vote?
            try:
                action_votes_yes = int(action_votes_yes)
                action_votes_no = int(action_votes_no)
                passed = None
                # some actions take a super majority, so we aren't just comparing the yeas and nays here.
                for i in vote_passage_indicators:
                    if action_name.count(i):
                        passed = True
                for i in vote_failure_indicators:
                    if action_name.count(i) and passed == True:
                        # a quick explanation:  originally an exception was
                        # thrown if both passage and failure indicators were
                        # present because I thought that would be a bug in my
                        # lists.  Then I found 2007 HB 160.
                        # Now passed = False if the nays outnumber the yays..
                        # I won't automatically mark it as passed if the yays
                        # ounumber the nays because I don't know what requires
                        # a supermajority in MT.  
                        if action_votes_no >= action_votes_yes:
                            passed = False
                        else:
                            raise Exception ("passage and failure indicator both present: %s" % action_name)
                    if action_name.count(i) and passed == None:
                        passed = False
                for i in vote_ambiguious_indicators:
                    if action_name.count(i):
                        passed = action_votes_yes > action_votes_no
                if passed is None:
                    raise Exception("Unknown passage: %s" % action_name)
                bill.add_vote(Vote(bill['chamber'],
                                   action_date,
                                   action_name,
                                   passed,
                                   action_votes_yes,
                                   action_votes_no,
                                   0))
            except ValueError:
                pass

            
    def add_sponsors(self, bill, status_page):
        for sponsor_row in status_page.xpath('/div/form[6]/table[1]/tr')[1:]:
            sponsor_type = sponsor_row.xpath("td[1]")[0].text
            sponsor_last_name = sponsor_row.xpath("td[2]")[0].text
            sponsor_first_name = sponsor_row.xpath("td[3]")[0].text
            sponsor_middle_initial = sponsor_row.xpath("td[4]")[0].text
            
            sponsor_middle_initial = sponsor_middle_initial.replace("&nbsp", "")
            sponsor_full_name = "%s, %s %s" % (sponsor_last_name,  sponsor_first_name, sponsor_middle_initial)
            sponsor_full_name = sponsor_full_name.strip()
            
            if sponsor_map.has_key(sponsor_type):
                sponsor_type = sponsor_map[sponsor_type]
            bill.add_sponsor(sponsor_type, sponsor_full_name)

    def add_bill_versions(self, bill, index_url):
        index_page = ElementTree(lxml.html.fromstring(self.urlopen(index_url)))
        tokens = bill['bill_id'].split(" ")
        bill_regex = re.compile("%s0*%s\_" % (tokens[0], tokens[1]))
        for anchor in index_page.findall('//a'):
            if bill_regex.match(anchor.text_content()) is not None:
                file_name = anchor.text_content()
                version = file_name[file_name.find('_')+1:file_name.find('.')]
                version_title = 'Final Version'
                if version != 'x':
                    version_title = 'Version %s' % version

                version_url = index_url[0:index_url.find('bills')-1] + anchor.attrib['href']
                bill.add_version(version_title, version_url)

if __name__ == '__main__':
    MTScraper.run()

    # scraper = MTScraper()
    # bill_url = 'http://data.opi.mt.gov/bills/2005/BillHtml/HB0790.htm'
    # scraper.parse_bill(bill_url, scraper.getSession(2005), 'lower')
