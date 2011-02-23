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
        'ADM': 'Administration',
        'CED': 'Commerce, Community & Economic Development',
        'COR': 'Corrections',
        'CRT': 'Court System',
        'EED': 'Education and Early Development',
        'DEC': 'Environmental Conservation ',
        'DFG': 'Fish and Game',
        'GOV': "Governor's Office",
        'DHS': 'Health and Social Services',
        'LWF': 'Labor and Workforce Development',
        'LAW': 'Law',
        'LEG': 'Legislative Agency',
        'MVA': "Military and Veterans' Affairs",
        'DNR': 'Natural Resources',
        'DPS': 'Public Safety',
        'REV': 'Revenue',
        'DOT': 'Transportation and Public Facilities',
        'UA': 'University of Alaska',
        'ALL': 'All Departments'}

    _comm_vote_type = {
        'DP': 'Do Pass',
        'DNP': 'Do Not Pass',
        'NR': 'No Recommendation',
        'AM': 'Amend'}

    _comm_mapping = {
        'CRA': 'Community & Regional Affairs',
        'EDC': 'Education',
        'FIN': 'Finance',
        'HSS': 'Health & Social Services',
        'JUD': 'Judiciary',
        'L&C': 'Labor & Commerce',
        'RES': 'Resources',
        'RLS': 'Rules',
        'STA': 'State Affairs',
        'TRA': 'Transportation',
        'EDT':'	Economic Development, Trade & Tourism',
        'ENE': 'Energy',
        'FSH': 'Fisheries',
        'MLV': 'Military & Veterans',
        'WTR': 'World Trade',
        'ARR': 'Administrative Regulation Review',
        'ASC': 'Armed Services Committee',
        'BUD': 'Legislative Budget & Audit',
        'ECR': 'Higher Education/Career Readiness Task Force',
        'EFF': 'Education Fuding District Cost Factor Committee',
        'ETH': 'Select Committee on Legislative Ethics',
        'LEC': 'Legislative Council',
}

    _comm_re = re.compile(r'^(%s)\s' % '|'.join(_comm_mapping.keys()))
    _current_comm = None

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

            if bill_id.startswith('HB') or bill_id.startswith('SB'):
                btype = ['bill']
            elif bill_id.startswith('SJR') or bill_id.startswith('HJR'):
                btype = ['joint resolution']
            elif bill_id.startswith('SR') or bill_id.startswith('HR'):
                btype = ['resolution']
            elif bill_id.startswith('SCR') or bill_id.startswith('HCR'):
                btype = ['concurrent resolution']

            if re.match(r'CONST\.? AM:', bill_name):
                btype.append('constitutional amendment')

            bill = Bill(session, chamber, bill_id, bill_name, type=btype)

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
                sponsor = sponsors[0].strip()

                if sponsor:
                    bill.add_sponsor('primary', sponsors[0])

                for sponsor in sponsors[1:]:
                    sponsor = sponsor.strip()
                    if sponsor:
                        bill.add_sponsor('cosponsor', sponsor)
            else:
                # Committee sponsorship
                spons_str = spons_str.strip()

                if re.match(r' BY REQUEST OF THE GOVERNOR$', spons_str):
                    spons_str = re.sub(r' BY REQUEST OF THE GOVERNOR$',
                                       '', spons_str).title()
                    spons_str = (spons_str +
                                 " Committee (by request of the governor)")

                if spons_str:
                    bill.add_sponsor('committee', spons_str)

            # Get actions
            self._current_comm = None
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
        yes, no, o1, o2, o3 = [0 if not x else int(x) for x in tally]
        other = o1 + o2 + o3

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
                    name = name.strip()
                    if name:
                        vote_type(name)

        vote.add_source(url)
        return vote

    def clean_action(self, action):
        # Clean up some acronyms
        match = re.match(r'^FN(\d+): (ZERO|INDETERMINATE)?\((\w+)\)', action)
        if match:
            num = match.group(1)

            if match.group(2) == 'ZERO':
                impact = 'No fiscal impact'
            elif match.group(2) == 'INDETERMINATE':
                impact = 'Indeterminate fiscal impact'
            else:
                impact = ''

            dept = match.group(3)
            dept = self._fiscal_dept_mapping.get(dept, dept)

            action = "Fiscal Note %s: %s (%s)" % (num, impact, dept)

        match = self._comm_re.match(action)
        if match:
            self._current_comm = match.group(1)

        match = re.match(r'^(DP|DNP|NR|AM):\s(.*)$', action)
        if match:
            vtype = self._comm_vote_type[match.group(1)]

            action = "%s %s: %s" % (self._current_comm, vtype,
                                    match.group(2))

        match = re.match(r'^COSPONSOR\(S\): (.*)$', action)
        if match:
            action = "Cosponsors added: %s" % match.group(1)

        match = re.match('^([A-Z]{3,3}), ([A-Z]{3,3})$', action)
        if match:
            action = "REFERRED TO %s and %s" % (
                self._comm_mapping[match.group(1)],
                self._comm_mapping[match.group(2)])

        match = re.match('^REFERRED TO (.*)$', action)
        if match:
            action = "REFERRED TO %s" % match.group(1).title()

        action = re.sub(r'\s+', ' ', action)

        action = action.replace('PREFILE RELEASED', 'Prefile released')

        atype = []
        if 'READ THE FIRST TIME' in action:
            atype.append('bill:introduced')
            atype.append('bill:reading:1')
            action = action.replace('READ THE FIRST TIME',
                                'Read the first time')
        if 'READ THE SECOND TIME' in action:
            atype.append('bill:reading:2')
            action = action.replace('READ THE SECOND TIME',
                                'Read the second time')
        if 'READ THE THIRD TIME' in action:
            atype.append('bill:reading:3')
            action = action.replace('READ THE THIRD TIME',
                                'Read the third time')
        if 'TRANSMITTED TO GOVERNOR' in action:
            atype.append('governor:received')
            action = action.replace('TRANSMITTED TO GOVERNOR',
                                'Transmitted to Governor')
        if 'SIGNED INTO LAW' in action:
            atype.append('governor:signed')
            action = action.replace('SIGNED INTO LAW', 'Signed into law')
        if 'Do Pass' in action:
            atype.append('committee:passed')
        if 'Do Not Pass' in action:
            atype.append('committee:failed')
        if action.startswith('PASSED'):
            atype.append('bill:passed')
        if 'REFERRED TO' in action:
            atype.append('committee:referred')
            action = action.replace('REFERRED TO', 'Referred to')

        return action, atype
