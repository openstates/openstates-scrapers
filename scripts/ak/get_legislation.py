#!/usr/bin/env python
import re
import datetime as dt
import csv
import html5lib

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import *

class AKLegislationScraper(LegislationScraper):

    state = 'ak'
    soup_parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    metadata = {
        'state_name': 'Alaska',
        'legislature_name': 'The Alaska State Legislature',
        'lower_chamber_name': 'House of Representatives',
        'upper_chamber_name': 'Senate',
        'lower_title': 'Representative',
        'upper_title': 'Senator',
        'lower_term': 2,
        'upper_term': 4,
        'sessions': ['18', '19', '20', '21', '22', '23', '24',
                     '25', '26'],
        'session_details': {
            '18': {'years': [1993, 1994], 'sub_sessions': [],
                   'election_year': 1992},
            '19': {'years': [1995, 1996], 'sub_sessions': [],
                   'election_year': 1994},
            '20': {'years': [1997, 1998], 'sub_sessions': [],
                   'election_year': 1996},
            '21': {'years': [1999, 2000], 'sub_sessions': [],
                   'election_year': 1998},
            '22': {'years': [2001, 2002], 'sub_sessions': [],
                   'election_year': 2000},
            '23': {'years': [2003, 2004], 'sub_sessions': [],
                   'election_year': 2002},
            '24': {'years': [2005, 2006], 'sub_sessions': [],
                   'election_year': 2004},
            '25': {'years': [2007, 2008], 'sub_sessions': [],
                   'election_year': 2006},
            '26': {'years': [2009, 2010], 'sub_sessions': [],
                   'election_year': 2008},
        }}

    def scrape_legislators(self, chamber, year):
        # Data available for 1993 on
        if int(year) < 1993 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # Expect first year of session (odd)
        if int(year) % 2 != 1:
            raise NoDataForYear(year)

        if chamber == 'upper':
            chamber_abbr = 'H'
        else:
            chamber_abbr = 'S'

        session = 18 + ((int(year) - 1993) / 2)

        leg_list_url = "http://www.legis.state.ak.us/basis/commbr_info.asp?session=%d" % session
        leg_list = self.soup_parser(self.urlopen(leg_list_url))

        leg_re = "get_mbr_info.asp\?member=.+&house=%s&session=%d" % (
            chamber_abbr, session)
        links = leg_list.findAll(href=re.compile(leg_re))

        for link in links:
            member_url = "http://www.legis.state.ak.us/basis/" + link['href']
            member_page = self.soup_parser(self.urlopen(member_url))

            full_name = member_page.findAll('h3')[1].contents[0]
            full_name = ' '.join(full_name.split(' ')[1:])
            full_name = re.sub('\s+', ' ', full_name).strip()

            first_name = full_name.split(' ')[0]
            last_name = full_name.split(' ')[-1]
            middle_name = ' '.join(full_name.split(' ')[1:-1])

            code = link['href'][24:27]

            district = member_page.find(text=re.compile("District:"))
            district = district.strip().split(' ')[-1]

            party = member_page.find(text=re.compile("Party: "))
            party = ' '.join(party.split(' ')[1:])

            self.add_legislator(Legislator(session, chamber, district,
                                           full_name, first_name,
                                           last_name, middle_name,
                                           party=party, code=code))

    def scrape_session(self, chamber, year):
        if chamber == 'upper':
            bill_abbr = 'SB|SCR|SJR'
        elif chamber == 'lower':
            bill_abbr = 'HB|HCR|HJR'

        # Sessions last 2 years, 1993-1994 was the 18th
        session = 18 + ((int(year) - 1993) / 2)
        year2 = str(int(year) + 1)

        # Full calendar year
        date1 = '0101' + year[2:]
        date2 = '1231' + year2[2:]

        # Get bill list
        bill_list_url = 'http://www.legis.state.ak.us/basis/range_multi.asp?session=%i&date1=%s&date2=%s' % (session, date1, date2)
        self.log("Getting bill list for %s %s (this may take a long time)." %
                 (chamber, session))
        bill_list = self.soup_parser(self.urlopen(bill_list_url))

        # Find bill links
        re_str = "bill=%s\d+" % bill_abbr
        links = bill_list.findAll(href=re.compile(re_str))

        for link in links:
            bill_id = link.contents[0].replace(' ', '')
            bill_name = link.parent.parent.findNext('td').find('font').contents[0].strip()
            bill = Bill(session, chamber, bill_id, bill_name.strip())

            # Get the bill info page and strip malformed t
            info_url = "http://www.legis.state.ak.us/basis/%s" % link['href']
            info_page = self.soup_parser(self.urlopen(info_url))

            # Get sponsors
            spons_str = info_page.find(
                text="SPONSOR(s):").parent.parent.contents[1]
            sponsors_match = re.match(
                ' (SENATOR|REPRESENTATIVE)\([Ss]\) ([^,]+(,[^,]+){0,})',
                spons_str)
            if sponsors_match:
                sponsors = sponsors_match.group(2).split(',')
                bill.add_sponsor('primary', sponsors[0].strip())

                for sponsor in sponsors[1:]:
                    bill.add_sponsor('cosponsor', sponsor.strip())
            else:
                # Committee sponsorship
                bill.add_sponsor('committee', spons_str.strip())

            # Get actions
            act_rows = info_page.findAll('table', 'myth')[1].findAll('tr')[1:]
            for row in act_rows:
                cols = row.findAll('td')
                act_date = cols[0].font.contents[0]

                if cols[2].font.string == "(H)":
                    act_chamber = "lower"
                elif cols[2].font.string == "(S)":
                    act_chamber = "upper"
                else:
                    act_chamber = chamber

                action = cols[3].font.contents[0].strip()

                bill.add_action(act_chamber, action, act_date)

            # Get subjects
            bill['subjects'] = []
            subject_link_re = re.compile('.*subject=\w+$')
            for subject_link in info_page.findAll('a', href=subject_link_re):
                subject = subject_link.contents[0].strip()
                bill['subjects'].append(subject)

            # Get versions
            text_list_url = "http://www.legis.state.ak.us/basis/get_fulltext.asp?session=%s&bill=%s" % (session, bill_id)
            text_list = self.soup_parser(self.urlopen(text_list_url))
            text_link_re = re.compile('^get_bill_text?')
            for text_link in text_list.findAll('a', href=text_link_re):
                text_name = text_link.parent.previousSibling.contents[0].strip()
                text_url = "http://www.legis.state.ak.us/basis/%s" % text_link['href']
                bill.add_version(text_name, text_url)

            self.add_bill(bill)

    def scrape_bills(self, chamber, year):
        # Data available for 1993 on
        if int(year) < 1993 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # Expect first year of session (odd)
        if int(year) % 2 != 1:
            raise NoDataForYear(year)

        self.scrape_session(chamber, year)

if __name__ == '__main__':
    AKLegislationScraper().run()
