import re
import datetime

import lxml.html

from pupa.scrape import Scraper, Bill, VoteEvent


class AKBillScraper(Scraper):
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
        'AET': 'Arctic Policy, Economic Development, & Tourism',
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
        'EDT': 'Economic Development, Trade & Tourism',
        'NRG': 'Energy',
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
        'ARC': 'Special Committee on the Arctic',
        'EDA': 'Economic Development, Trade, Tourism & Arctic Policy',
        'ENE': 'Energy',
    }

    _comm_re = re.compile(r'^(%s)\s' % '|'.join(_comm_mapping.keys()))
    _current_comm = None

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        bill_types = {'B': 'bill', 'R': 'resolution', 'JR': 'joint resolution',
                      'CR': 'concurrent resolution'}

        bill_list_url = (
            'https://www.akleg.gov/basis/Bill/Range/%s'
        ) % (session)
        doc = lxml.html.fromstring(self.get(bill_list_url).text)
        doc.make_links_absolute(bill_list_url)
        for bill_link in doc.xpath('//tr//td[1]//nobr[1]//a[1]'):
            bill_abbr = bill_link.text
            if ' ' in bill_abbr:
                bill_abbr = bill_abbr.split(' ')[0]
            elif 'HCR' in bill_abbr:
                bill_abbr = bill_abbr[:3]
            else:
                bill_abbr = bill_abbr[:2]
            bill_id = bill_link.text.replace(' ', '')
            bill_type = bill_types[bill_abbr[1:]]
            bill_url = bill_link.get('href').replace(' ', '')
            if bill_abbr in ['SB', 'SR', 'SCR', 'SJR']:
                chamber = 'upper'
            else:
                chamber = 'lower'

            yield from self.scrape_bill(chamber, session, bill_id, bill_type,
                                        bill_url)


    def scrape_bill(self, chamber, session, bill_id, bill_type, url):
        doc = lxml.html.fromstring(self.get(url).text)
        doc.make_links_absolute(url)

        title = doc.xpath('//span[text()="Title"]')[0].getparent()
        if title:
            title = title[1].text.strip().strip('"')
        else:
            self.warning("skipping bill %s, no information" % url)
            return

        bill = Bill(
            bill_id,
            title=title,
            chamber=chamber,
            classification=bill_type,
            legislative_session=session,
        )
        bill.add_source(url)

        # Get sponsors
        spons_str = doc.xpath('//span[contains(text(), "Sponsor(S)")]')[0].getparent()[1].text
        sponsors_match = re.match(
            r'(SENATOR|REPRESENTATIVE)',
            spons_str)
        
        if sponsors_match:
            sponsors = spons_str.split(',')
            sponsor = sponsors[0].strip()

            if sponsor:
                bill.add_sponsorship(
                    sponsors[0].split()[1],
                    entity_type='person',
                    classification='primary',
                    primary=True,
                )
                

            for sponsor in sponsors[1:]:
                sponsor = sponsor.strip()
                if sponsor:
                    bill.add_sponsorship(
                        sponsor,
                        entity_type='person',
                        classification='cosponsor',
                        primary=False,
                    )
                    
        else:
            # Committee sponsorship
            spons_str = spons_str.strip()

            if re.match(r' BY REQUEST OF THE GOVERNOR$', spons_str):
                spons_str = re.sub(r' BY REQUEST OF THE GOVERNOR$',
                                   '', spons_str).title()
                spons_str = (spons_str +
                             " Committee (by request of the governor)")

            if spons_str:
                bill.add_sponsorship(
                    spons_str,
                    entity_type='person',
                    classification='primary',
                    primary=True,
                )

        # Get actions
        self._current_comm = None
        act_rows = doc.xpath("//div[@id='tab6_4']//tr")[1:]
        for row in act_rows:
            date, journal, action = row.xpath('td')
            action = action.text_content().strip()
            raw_chamber = action[0:3]
            journal_entry_number = journal.text_content()
            act_date = datetime.datetime.strptime(date.text_content().strip(), '%m/%d/%Y')
            

            if raw_chamber == "(H)":
                act_chamber = "lower"
            elif raw_chamber == "(S)":
                act_chamber = "upper"

            # Votes
            if re.search(r"Y(\d+)", action):
                vote_href = journal.xpath('.//a/@href')
                if vote_href:
                    vote_href = vote_href[0].replace(' ', '')
                    yield from self.parse_vote(bill, journal_entry_number, action, act_chamber, act_date, vote_href)


            action, atype = self.clean_action(action)

            match = re.search(r'^Prefile released (\d+/\d+/\d+)$', action)
            if match:
                action = 'Prefile released'
                act_date = datetime.datetime.strptime(match.group(1), '%m/%d/%y')

            bill.add_action(
                action, chamber=act_chamber, date=act_date.strftime('%Y-%m-%d'),
                classification=atype)

        # Get subjects
        for subj in doc.xpath('//a[contains(@href, "subject")]/text()'):
            bill.add_subject(subj.strip())

        # Get versions - to do
        text_list_url = (
            "https://www.akleg.gov/basis/Bill/Detail/%s?Root=%s#tab1_4") % (session, bill_id)
        bill.add_source(text_list_url)

        text_doc = lxml.html.fromstring(self.get(text_list_url).text)
        text_doc.make_links_absolute(text_list_url)
        for link in text_doc.xpath('//a[contains(@href, "/Text/")]'):
            name = link.text_content()
            text_url = link.get('href')
            bill.add_version_link(name, text_url, media_type="text/html")

        # Get documents - to do
        doc_list_url = (
            "https://www.akleg.gov/basis/Bill/Detail/%s?Root=%s#tab5_4") % (session, bill_id)
        doc_list = lxml.html.fromstring(self.get(doc_list_url).text)
        doc_list.make_links_absolute(doc_list_url)
        bill.add_source(doc_list_url)
        for href in doc_list.xpath('//a[contains(@href, "get_documents")][@onclick]'):
            h_name = href.text_content()
            h_href = href.attrib['href']
            if h_name.strip():
                try:
                    bill.add_document_link(h_name, h_href)
                except:
                    print("Duplicate found")

        yield bill

    def parse_vote(self, bill, journal_entry_number, action, act_chamber, act_date, url):
        
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        yes = no = other = 0
        vote_counts = action.split()
        for vote_count in vote_counts:
            if re.match(r'[\D][\d]', vote_count):
                if "Y" in vote_count:
                    yes = int(vote_count[1:])
                elif "N" in vote_count:
                    no = int(vote_count[1:])
                elif "E" in vote_count or "A" in vote_count:
                    other += int(vote_count[1:])


        vote = VoteEvent(
                bill=bill,
                start_date=act_date.strftime('%Y-%m-%d'),
                chamber=act_chamber,
                motion_text=action,
                result='pass' if yes > no else 'fail',
                classification='passage',
                )

        vote.set_count('yes', yes)
        vote.set_count('no', no)
        vote.set_count('other', other)
        vote.add_source(url)

        yield vote

        
        # print(action)

        # Dan attempt at pulling out the vote information
        # Xpath to grab journal entry information
        # xpath_search = "//b[text()[contains(.,'%s')]]" % journal_entry_number
        # xpath_search = "//body//pre[1]"
        # vote_counts = doc.xpath(xpath_search)
        # print(vote_counts[0].text_content().split("\n"))
        # vote_counts = doc.xpath('//body//b[contains(text(), "YEAS")]')
        # for votes in vote_counts:
        #     print(votes.text_content())


        # yield vote

        # old code
        # re_vote_text = re.compile(r'The question (?:being|to be reconsidered):\s*"(.*?\?)"', re.S)
        # re_header = re.compile(r'\d{2}-\d{2}-\d{4}\s{10,}\w{,20} Journal\s{10,}\d{,6}\s{,4}')

        # if len(doc.xpath('//pre')) < 2:
        #     return

        # Find all chunks of text representing voting reports.
        # votes_text = doc.xpath('//pre')[1].text_content()
        # votes_text = re_vote_text.split(votes_text)
        # votes_data = zip(votes_text[1::2], votes_text[2::2])
        # votes_data = []
        

        # iVoteOnPage = 0

        # # Process each.
        # votes_data = []
        # for motion, text in votes_data:

        #     iVoteOnPage += 1
        #     yes = no = other = 0

        #     tally = re.findall(r'\b([YNEA])[A-Z]+:\s{,3}(\d{,3})', text)
        #     for vtype, vcount in tally:
        #         vcount = int(vcount) if vcount != '-' else 0
        #         if vtype == 'Y':
        #             yes = vcount
        #         elif vtype == 'N':
        #             no = vcount
        #         else:
        #             other += vcount

        #     vote = VoteEvent(
        #         bill=bill,
        #         start_date=act_date.strftime('%Y-%m-%d'),
        #         chamber=act_chamber,
        #         motion_text=motion,
        #         result='pass' if yes > no else 'fail',
        #         classification='passage',
        #     )
        #     vote.set_count('yes', yes)
        #     vote.set_count('no', no)
        #     vote.set_count('other', other)
        #     print("Yes votes:", yes, "No votes", no, "Other", other)

        #     vote.pupa_id = (url + ' ' + str(iVoteOnPage)) if iVoteOnPage > 1 else url

        #     # In lengthy documents, the "header" can be repeated in the middle
        #     # of content. This regex gets rid of it.
        #     vote_lines = re_header.sub('', text)
        #     vote_lines = vote_lines.split('\r\n')

        #     vote_type = None
        #     for vote_list in vote_lines:
        #         if vote_list.startswith('Yeas: '):
        #             vote_list, vote_type = vote_list[6:], 'yes'
        #         elif vote_list.startswith('Nays: '):
        #             vote_list, vote_type = vote_list[6:], 'no'
        #         elif vote_list.startswith('Excused: '):
        #             vote_list, vote_type = vote_list[9:], 'other'
        #         elif vote_list.startswith('Absent: '):
        #             vote_list, vote_type = vote_list[9:], 'other'
        #         elif vote_list.strip() == '':
        #             vote_type = None
        #         if vote_type:
        #             for name in vote_list.split(','):
        #                 name = name.strip()
        #                 if name:
        #                     vote.vote(vote_type, name)

        #     vote.add_source(url)

            # yield vote



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

        match = re.match('^([A-Z]{3,3})$', action)
        if match:
            action = 'REFERRED TO %s' % self._comm_mapping[action]

        match = re.match('^REFERRED TO (.*)$', action)
        if match:
            comms = match.group(1).title().replace(' And ', ' and ')
            action = "REFERRED TO %s" % comms

        action = re.sub(r'\s+', ' ', action)

        action = action.replace('PREFILE RELEASED', 'Prefile released')

        atype = []
        if 'READ THE FIRST TIME' in action:
            atype.append('introduction')
            atype.append('reading-1')
            action = action.replace('READ THE FIRST TIME',
                                    'Read the first time')
        if 'READ THE SECOND TIME' in action:
            atype.append('reading-2')
            action = action.replace('READ THE SECOND TIME',
                                    'Read the second time')
        if 'READ THE THIRD TIME' in action:
            atype.append('reading-3')
            action = action.replace('READ THE THIRD TIME',
                                    'Read the third time')
        if 'TRANSMITTED TO GOVERNOR' in action:
            atype.append('executive-receipt')
            action = action.replace('TRANSMITTED TO GOVERNOR',
                                    'Transmitted to Governor')
        if 'SIGNED INTO LAW' in action:
            atype.append('executive-signature')
            action = action.replace('SIGNED INTO LAW', 'Signed into law')
        if 'Do Pass' in action:
            atype.append('committee-passage')
        if 'Do Not Pass' in action:
            atype.append('committee-failure')
        if action.startswith('PASSED'):
            atype.append('passage')
        if 'REFERRED TO' in action:
            atype.append('referral-committee')
            action = action.replace('REFERRED TO', 'Referred to')
        if 'Prefile released' in action:
            atype.append('filing')

        return action, atype
