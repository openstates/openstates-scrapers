import re
import datetime as dt

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import html5lib


class AKBillScraper(BillScraper):
    state = 'ak'
    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    _fiscal_dept_mapping = {
        'ADM': 'ADMINISTRATION',
        'CED': 'COMMERCE, COMMUNITY & ECONOMIC DEVELOPMENT',
        'COR': 'CORRECTIONS',
        'CRT': 'COURT SYSTEM',
        'EED': 'EDUCATION AND EARLY DEVELOPMENT',
        'DEC': 'ENVIRONMENTAL CONSERVATION ',
        'DFG': 'FISH AND GAME',
        'GOV': 'GOVERNOR\'S OFFICE',
        'DHS': 'HEALTH AND SOCIAL SERVICES',
        'LWF': 'LABOR AND WORKFORCE DEVELOPMENT',
        'LAW': 'LAW',
        'LEG': 'LEGISLATIVE AGENCY',
        'MVA': 'MILITARY AND VETERANS\' AFFAIRS',
        'DNR': 'NATURAL RESOURCES',
        'DPS': 'PUBLIC SAFETY',
        'REV': 'REVENUE',
        'DOT': 'TRANSPORTATION AND PUBLIC FACILITIES',
        'UA': 'UNIVERSITY OF ALASKA',
        'ALL': 'ALL DEPARTMENTS'}

    def scrape(self, chamber, session):
        for term in self.metadata['terms']:
            if term['sessions'][0] == session:
                year = str(term['start_year'])
                year2 = str(term['end_year'])
                break
        else:
            raise NoDataForPeriod(session)

        if chamber == 'upper':
            bill_abbr = 'SB|SCR|SJR'
        elif chamber == 'lower':
            bill_abbr = 'HB|HCR|HJR'

        # Full calendar year
        date1 = '0101' + year[2:]
        date2 = '1231' + year2[2:]

        # Get bill list
        bill_list_url = 'http://www.legis.state.ak.us/'\
            'basis/range_multi.asp?session=%s&date1=%s&date2=%s' % (
            session, date1, date2)
        self.log("Getting bill list for %s %s (this may take a long time)." %
                 (chamber, session))
        bill_list = self.soup_parser(self.urlopen(bill_list_url))

        # Find bill links
        re_str = "bill=%s\d+" % bill_abbr
        links = bill_list.findAll(href=re.compile(re_str))

        for link in links:
            bill_id = link.contents[0].replace(' ', '')
            bill_name = link.parent.parent.findNext('td').find(
                'font').contents[0].strip()
            bill = Bill(session, chamber, bill_id, bill_name.strip())

            # Get the bill info page and strip malformed t
            info_url = "http://www.legis.state.ak.us/basis/%s" % link['href']
            info_page = self.soup_parser(self.urlopen(info_url))
            bill.add_source(info_url)

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
                act_date = dt.datetime.strptime(act_date, '%m/%d/%y')

                if cols[2].font.string == "(H)":
                    act_chamber = "lower"
                elif cols[2].font.string == "(S)":
                    act_chamber = "upper"
                else:
                    act_chamber = chamber

                action = cols[3].font.contents[0].strip()
                if re.match("\w+ Y(\d+) N(\d+)", action):
                    try:
                        vote = self.parse_vote(bill, action,
                                               act_chamber, act_date,
                                               cols[1].a['href'])
                        bill.add_vote(vote)
                    except:
                        self.log("Failed parsing vote at %s" %
                                 cols[1].a['href'])

                action, atype = self.clean_action(action)

                bill.add_action(act_chamber, action, act_date, type=atype)

            # Get subjects
            bill['subjects'] = []
            subject_link_re = re.compile('.*subject=\w+$')
            for subject_link in info_page.findAll('a', href=subject_link_re):
                subject = subject_link.contents[0].strip()
                bill['subjects'].append(subject)

            # Get versions
            text_list_url = "http://www.legis.state.ak.us/"\
                "basis/get_fulltext.asp?session=%s&bill=%s" % (
                session, bill_id)
            text_list = self.soup_parser(self.urlopen(text_list_url))
            bill.add_source(text_list_url)

            text_link_re = re.compile('^get_bill_text?')
            for text_link in text_list.findAll('a', href=text_link_re):
                text_name = text_link.parent.previousSibling.contents[0]
                text_name = text_name.strip()

                text_url = "http://www.legis.state.ak.us/basis/%s" % (
                    text_link['href'])

                bill.add_version(text_name, text_url)

            self.save_bill(bill)

    def parse_vote(self, bill, action, act_chamber, act_date, url):
        url = "http://www.legis.state.ak.us/basis/%s" % url
        info_page = self.soup_parser(self.urlopen(url))

        tally = re.findall('Y(\d+) N(\d+)\s*(?:\w(\d+))*\s*(?:\w(\d+))*'
                           '\s*(?:\w(\d+))*', action)[0]
        yes, no, o1, o2, o3 = map(lambda x: 0 if x == '' else int(x), tally)
        yes, no, other = int(yes), int(no), (int(o1) + int(o2) + int(o3))

        votes = info_page.findAll('pre', text=re.compile('Yeas'),
                                  limit=1)[0].split('\n\n')

        motion = info_page.findAll(text=re.compile('The question being'))[0]
        motion = re.findall('The question being:\s*"(.*)\?"',
                            motion, re.DOTALL)[0].replace('\n', ' ')

        vote = Vote(act_chamber, act_date, motion, yes > no, yes, no, other)

        for vote_list in votes:
            vote_type = False
            if vote_list.startswith('Yeas: '):
                vote_list, vote_type = vote_list[6:], vote.yes
            elif vote_list.startswith('Nays: '):
                vote_list, vote_type = vote_list[6:], vote.no
            elif vote_list.startswith('Excused: '):
                vote_list, vote_type = vote_list[9:], vote.other
            elif vote_list.startswith('Absent: '):
                vote_list, vote_type = vote_list[9:], vote.other
            if vote_type:
                for name in vote_list.split(','):
                    vote_type(name.strip())

        vote.add_source(url)
        return vote

    def clean_action(self, action):
        # Clean up some acronyms
        match = re.match(r'^FN(\d+): (ZERO|INDETERMINATE)?\((\w+)\)', action)
        if match:
            num = match.group(1)

            if match.group(2) == 'ZERO':
                impact = 'NO FISCAL IMPACT'
            elif match.group(2) == 'INDETERMINATE':
                impact = 'INDETERMINATE FISCAL IMPACT'
            else:
                impact = ''

            dept = match.group(3)
            dept = self._fiscal_dept_mapping.get(dept, dept)

            action = "FISCAL NOTE %s: %s (%s)" % (num, impact, dept)

        action = re.sub(r'\s+', ' ', action)

        atype = []
        if 'READ THE FIRST TIME' in action:
            atype.append('bill:introduced')
            atype.append('bill:reading:1')
        if 'READ THE SECOND TIME' in action:
            atype.append('bill:reading:2')
        if 'READ THE THIRD TIME' in action:
            atype.append('bill:reading:3')
        if 'TRANSMITTED TO GOVERNOR' in action:
            atype.append('governor:received')
        if 'SIGNED INTO LAW' in action:
            atype.append('governor:signed')

        return action, atype
