import re
import datetime
from urllib.parse import urlencode
from collections import defaultdict
from pupa.scrape import Scraper, Bill, VoteEvent
from pupa.utils import format_datetime
from spatula import Page, PDF, Spatula


class StartPage(Page):

    def handle_page(self):
        try:
            pages = int(self.doc.xpath("//a[contains(., 'Next')][1]/preceding::a[1]/text()")[0])
        except IndexError:
            if not self.doc.xpath('//div[@class="ListPagination"]/span'):
                raise AssertionError("No bills found for the session")
            elif set(self.doc.xpath('//div[@class="ListPagination"]/span/text()')) != set(["1"]):
                raise AssertionError("Bill list pagination needed but not used")
            else:
                self.scraper.warning("Pagination not used; "
                                     "make sure there are only a few bills for this session")
            pages = 1

        for page_number in range(1, pages + 1):
            page_url = (self.url + '&PageNumber={}'.format(page_number))
            yield from self.scrape_page_items(BillList, url=page_url,
                                              session=self.kwargs['session'],
                                              subjects=self.kwargs['subjects'],
                                              )


class BillList(Page):
    list_xpath = "//a[contains(@href, '/Session/Bill/')]"

    def handle_list_item(self, item):
        bill_id = item.text.strip()
        title = item.xpath("string(../following-sibling::td[1])").strip()
        sponsor = item.xpath("string(../following-sibling::td[2])").strip()
        bill_url = item.attrib['href'] + '/ByCategory'

        if bill_id.startswith(('SB ', 'HB ', 'SPB ', 'HPB ')):
            bill_type = 'bill'
        elif bill_id.startswith(('HR ', 'SR ')):
            bill_type = 'resolution'
        elif bill_id.startswith(('HJR ', 'SJR ')):
            bill_type = 'joint resolution'
        elif bill_id.startswith(('SCR ', 'HCR ')):
            bill_type = 'concurrent resolution'
        elif bill_id.startswith(('SM ', 'HM ')):
            bill_type = 'memorial'
        else:
            raise ValueError('Failed to identify bill type.')

        bill = Bill(bill_id, self.kwargs['session'], title,
                    chamber='lower' if bill_id[0] == 'H' else 'upper',
                    classification=bill_type)
        bill.add_source(bill_url)

        # normalize id from HB 0004 to H4
        subj_bill_id = re.sub('(H|S)\w+ 0*(\d+)', r'\1\2', bill_id)
        bill.subject = sorted(list(self.kwargs['subjects'][subj_bill_id]))

        sponsor = re.sub(r'^(?:Rep|Sen)\.\s', "", sponsor)
        for sp in sponsor.split(', '):
            bill.add_sponsorship(sp.strip(), 'primary', 'person', True)

        yield from self.scrape_page_items(BillDetail, url=bill_url, obj=bill)

        yield bill


class BillDetail(Page):

    def handle_page(self):
        self.process_history()
        self.process_versions()
        self.process_analysis()
        yield from self.process_votes()
        yield from self.scrape_page_items(HousePage, bill=self.obj)

    def process_versions(self):
        try:
            version_table = self.doc.xpath("//div[@id = 'tabBodyBillText']/table")[0]
            for tr in version_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                version_url = tr.xpath("td/a[1]")[0].attrib['href']
                if version_url.endswith('PDF'):
                    mimetype = 'application/pdf'
                    text = self.scrape_page(BillVersionPDF, url=version_url)
                elif version_url.endswith('HTML'):
                    mimetype = 'text/html'
                    text = self.scrape_page(BillVersionHTML, url=version_url)

                self.obj.add_version_link(name, version_url, media_type=mimetype, text=text)
        except IndexError:
            self.obj.extras['places'] = []   # set places to something no matter what
            self.scraper.warning("No version table for {}".format(self.obj.identifier))

    def process_analysis(self):
        try:
            analysis_table = self.doc.xpath("//div[@id = 'tabBodyAnalyses']/table")[0]
            for tr in analysis_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                name += " -- " + tr.xpath("string(td[3])").strip()
                name = re.sub(r'\s+', " ", name)
                date = tr.xpath("string(td[4])").strip()
                if date:
                    name += " (%s)" % date
                analysis_url = tr.xpath("td/a")[0].attrib['href']
                self.obj.add_document_link(name, analysis_url, on_duplicate='ignore')
        except IndexError:
            self.scraper.warning("No analysis table for {}".format(self.obj.identifier))

    def process_history(self):
        hist_table = self.doc.xpath("//div[@id = 'tabBodyBillHistory']//table")[0]

        for tr in hist_table.xpath("tbody/tr"):
            date = tr.xpath("string(td[1])")
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date().isoformat()

            actor = tr.xpath("string(td[2])")
            if not actor:
                actor = None
            chamber = {'Senate': 'upper', 'House': 'lower'}.get(actor, None)
            if chamber:
                actor = None

            act_text = tr.xpath("string(td[3])").strip()
            for action in act_text.split(u'\u2022'):
                action = action.strip()
                if not action:
                    continue

                action = re.sub(r'-(H|S)J\s+(\d+)$', '', action)

                atype = []
                if action.startswith('Referred to'):
                    atype.append('referral-committee')
                elif action.startswith('Favorable by'):
                    atype.append('committee-passage-favorable')
                elif action == "Filed":
                    atype.append("filing")
                elif action.startswith("Withdrawn"):
                    atype.append("withdrawal")
                elif action.startswith("Died"):
                    atype.append("failure")
                elif action.startswith('Introduced'):
                    atype.append('introduction')
                elif action.startswith('Read 2nd time'):
                    atype.append('reading-2')
                elif action.startswith('Read 3rd time'):
                    atype.append('reading-3')
                elif action.startswith('Adopted'):
                    atype.append('passage')
                elif action.startswith('CS passed'):
                    atype.append('passage')
                elif action == 'Approved by Governor':
                    atype.append('executive-signature')
                elif action == 'Vetoed by Governor':
                    atype.append('executive-veto')

                self.obj.add_action(action, date, organization=actor, chamber=chamber,
                                    classification=atype)

    def process_votes(self):
        vote_tables = self.doc.xpath("//div[@id='tabBodyVoteHistory']//table")

        for vote_table in vote_tables:
            for tr in vote_table.xpath("tbody/tr"):
                vote_date = tr.xpath("string(td[3])").strip()
                if vote_date.isalpha():
                    vote_date = tr.xpath("string(td[2])").strip()
                try:
                    vote_date = datetime.datetime.strptime(vote_date, "%m/%d/%Y %H:%M %p")
                except ValueError:
                    self.scraper.logger.warning('bad vote date: {}'.format(vote_date))

                vote_date = format_datetime(vote_date, 'US/Eastern')

                vote_url = tr.xpath("td[4]/a")[0].attrib['href']
                if "SenateVote" in vote_url:
                    yield from self.scrape_page_items(FloorVote, vote_url,
                                                      date=vote_date, chamber='upper',
                                                      bill=self.obj)
                elif "HouseVote" in vote_url:
                    yield from self.scrape_page_items(FloorVote, vote_url,
                                                      date=vote_date, chamber='lower',
                                                      bill=self.obj)
                else:
                    yield from self.scrape_page_items(UpperComVote, vote_url,
                                                      date=vote_date, bill=self.obj)
        else:
            self.scraper.warning("No vote table for {}".format(self.obj.identifier))


class BillVersionHTML(Page):
    def handle_page(self):
        text = self.doc.xpath('//pre')[0].text_content()
        text = re.sub('\n\s*\d+\s*', ' ', text)
        text = re.sub('\s+', ' ', text)
        return text


class BillVersionPDF(PDF):
    def handle_page(self):
        # newlines followed by numbers and lots of spaces
        text = re.sub('\n\s*\d+\s*', ' ', self.text)
        flhor_re = '\s+'.join('FLORIDA HOUSE OF REPRESENTATIVES')
        text = re.sub(flhor_re, ' ', text)
        # collapse spaces
        text = re.sub('\s+', ' ', text)
        return text


class FloorVote(PDF):
    def handle_page(self):
        MOTION_INDEX = 4
        TOTALS_INDEX = 6
        VOTE_START_INDEX = 9

        if len(self.lines) < 2:
            self.scraper.warning("Bad PDF! " + self.url)
            return

        motion = self.lines[MOTION_INDEX].strip()
        # Sometimes there is no motion name, only "Passage" in the line above
        if (not motion and not self.lines[MOTION_INDEX - 1].startswith("Calendar Page:")):
            motion = self.lines[MOTION_INDEX - 1]
            MOTION_INDEX -= 1
            TOTALS_INDEX -= 1
            VOTE_START_INDEX -= 1
        else:
            assert motion, "Floor vote's motion name appears to be empty"

        for _extra_motion_line in range(2):
            MOTION_INDEX += 1
            if self.lines[MOTION_INDEX].strip():
                motion = "{}, {}".format(motion, self.lines[MOTION_INDEX].strip())
                TOTALS_INDEX += 1
                VOTE_START_INDEX += 1
            else:
                break

        (yes_count, no_count, nv_count) = [
            int(x) for x in re.search(r'^\s+Yeas - (\d+)\s+Nays - (\d+)\s+Not Voting - (\d+)\s*$',
                                      self.lines[TOTALS_INDEX]).groups()
        ]
        result = 'pass' if yes_count > no_count else 'fail'

        vote = VoteEvent(start_date=self.kwargs['date'],
                         chamber=self.kwargs['chamber'],
                         bill=self.kwargs['bill'],
                         motion_text=motion,
                         result=result,
                         classification='passage',
                         )
        vote.add_source(self.url)
        vote.set_count('yes', yes_count)
        vote.set_count('no', no_count)
        vote.set_count('not voting', nv_count)

        for line in self.lines[VOTE_START_INDEX:]:
            if not line.strip():
                break

            if " President " in line:
                line = line.replace(" President ", " ")
            elif " Speaker " in line:
                line = line.replace(" Speaker ", " ")

            # Votes follow the pattern of:
            # [vote code] [member name]-[district number]
            for vtype, member in re.findall(r'\s*(Y|N|EX|AV)\s+(.*?)-\d{1,3}\s*', line):
                vtype = {'Y': 'yes', 'N': 'no', 'EX': 'excused', 'AV': 'abstain'}[vtype]
                vote.vote(vtype, member)

        # check totals line up
        yes_count = no_count = nv_count = 0
        for vc in vote.counts:
            if vc['option'] == 'yes':
                yes_count = vc['value']
            elif vc['option'] == 'no':
                no_count = vc['value']
            else:
                nv_count += vc['value']

        for vr in vote.votes:
            if vr['option'] == 'yes':
                yes_count -= 1
            elif vr['option'] == 'no':
                no_count -= 1
            else:
                nv_count -= 1

        if yes_count != 0 or no_count != 0:
            raise ValueError('vote count incorrect: ' + self.url)

        if nv_count != 0:
            # On a rare occasion, a member won't have a vote code,
            # which indicates that they didn't vote. The totals reflect
            # this.
            self.scraper.info("Votes don't add up; looking for additional ones")
            for line in self.lines[VOTE_START_INDEX:]:
                if not line.strip():
                    break
                for member in re.findall(r'\s{8,}([A-Z][a-z\'].*?)-\d{1,3}', line):
                    vote.vote('not voting', member)
        yield vote


class UpperComVote(PDF):

    def handle_page(self):
        (_, motion) = self.lines[5].split("FINAL ACTION:")
        motion = motion.strip()
        if not motion:
            self.scraper.warning("Vote appears to be empty")
            return

        vote_top_row = [self.lines.index(x) for x in self.lines if
                        re.search(r'^\s+Yea\s+Nay.*?(?:\s+Yea\s+Nay)+$', x)][0]
        yea_columns_end = self.lines[vote_top_row].index("Yea") + len("Yea")
        nay_columns_begin = self.lines[vote_top_row].index("Nay")

        votes = {'yes': [], 'no': [], 'other': []}
        for line in self.lines[(vote_top_row + 1):]:
            if line.strip():
                member = re.search(r'''(?x)
                        ^\s+(?:[A-Z\-]+)?\s+    # Possible vote indicator
                        ([A-Z][a-z]+            # Name must have lower-case characters
                        [\w\-\s]+)              # Continue looking for the rest of the name
                        (?:,[A-Z\s]+?)?         # Leadership has an all-caps title
                        (?:\s{2,}.*)?           # Name ends when many spaces are seen
                        ''', line).group(1)
                # sometimes members have trailing X's from other motions in the
                # vote sheet we aren't collecting
                member = re.sub('(\s+X)+', '', member)
                # Usually non-voting members won't even have a code listed
                # Only a couple of codes indicate an actual vote:
                # "VA" (vote after roll call) and "VC" (vote change)
                did_vote = bool(re.search(r'^\s+(X|VA|VC)\s+[A-Z][a-z]', line))
                if did_vote:
                    # Check where the "X" or vote code is on the page
                    vote_column = len(line) - len(line.lstrip())
                    if vote_column <= yea_columns_end:
                        votes['yes'].append(member)
                    elif vote_column >= nay_columns_begin:
                        votes['no'].append(member)
                    else:
                        raise ValueError("Unparseable vote found for {0} in {1}:\n{2}"
                                         .format(member, self.url, line))
                else:
                    votes['other'].append(member)

            # End loop as soon as no more members are found
            else:
                break

        totals = re.search(r'(?msu)\s+(\d{1,3})\s+(\d{1,3})\s+.*?TOTALS', self.text).groups()
        yes_count = int(totals[0])
        no_count = int(totals[1])
        result = 'pass' if (yes_count > no_count) else 'fail'

        vote = VoteEvent(start_date=self.kwargs['date'],
                         bill=self.kwargs['bill'],
                         chamber='upper',
                         motion_text=motion,
                         classification='committee',
                         result=result
                         )
        vote.add_source(self.url)
        vote.set_count('yes', yes_count)
        vote.set_count('no', no_count)
        vote.set_count('other', len(votes['other']))

        # set voters
        for vtype, voters in votes.items():
            for voter in voters:
                vote.vote(vtype, voter)

        yield vote


class HousePage(Page):
    '''
    House committee roll calls are not available on the Senate's
    website. Furthermore, the House uses an internal ID system in
    its URLs, making accessing those pages non-trivial.

    This will fetch all the House committee votes for the
    given bill, and add the votes to that object.
    '''
    url = 'http://www.myfloridahouse.gov/Sections/Bills/bills.aspx'
    list_xpath = '//a[contains(@href, "/Bills/billsdetail.aspx?BillId=")]/@href'

    def do_request(self):
        # Keep the digits and all following characters in the bill's ID
        bill_number = re.search(r'^\w+\s(\d+\w*)$', self.kwargs['bill'].identifier).group(1)
        session_number = {
            '2019': '87',
            '2018': '86',
            '2017A': '85',
            '2017': '83',
            '2016': '80',
            '2015C': '82',
            '2015B': '81',
            '2015A': '79',
            '2015': '76',
            '2014O': '78',
            '2014A': '77',
            '2016O': '84',
        }[self.kwargs['bill'].legislative_session]

        form = {
            'Chamber': 'B',
            'SessionId': session_number,
            'BillNumber': bill_number,
        }
        return self.scraper.get(self.url + '?' + urlencode(form))

    def handle_list_item(self, item):
        yield from self.scrape_page_items(HouseBillPage, item, bill=self.kwargs['bill'])


class HouseBillPage(Page):
    list_xpath = '//a[text()="See Votes"]/@href'

    def handle_list_item(self, item):
        yield from self.scrape_page_items(HouseComVote, item, bill=self.kwargs['bill'])


class HouseComVote(Page):

    def handle_page(self):
        (date, ) = self.doc.xpath('//span[@id="ctl00_ContentPlaceHolder1_lblDate"]/text()')
        date = format_datetime(datetime.datetime.strptime(date, '%m/%d/%Y %I:%M:%S %p'),
                               'US/Eastern')

        totals = self.doc.xpath('//table//table')[-1].text_content()
        totals = re.sub(r'(?mu)\s+', " ", totals).strip()
        (yes_count, no_count, other_count) = [int(x) for x in re.search(
            r'(?m)Total Yeas:\s+(\d+)\s+Total Nays:\s+(\d+)\s+'
            'Total Missed:\s+(\d+)', totals).groups()]
        result = 'pass' if yes_count > no_count else 'fail'

        (committee, ) = self.doc.xpath(
            '//span[@id="ctl00_ContentPlaceHolder1_lblCommittee"]/text()')
        (action, ) = self.doc.xpath('//span[@id="ctl00_ContentPlaceHolder1_lblAction"]/text()')
        motion = "{} ({})".format(action, committee)

        vote = VoteEvent(start_date=date,
                         bill=self.kwargs['bill'],
                         chamber='lower',
                         motion_text=motion,
                         result=result,
                         classification='committee',
                         )
        vote.add_source(self.url)
        vote.set_count('yes', yes_count)
        vote.set_count('no', no_count)
        vote.set_count('not voting', other_count)

        for member_vote in self.doc.xpath('//table//table//table//td'):
            if not member_vote.text_content().strip():
                continue

            (member, ) = member_vote.xpath('span[2]//text()')
            (member_vote, ) = member_vote.xpath('span[1]//text()')

            if member_vote == "Y":
                vote.yes(member)
            elif member_vote == "N":
                vote.no(member)
            elif member_vote == "-":
                vote.vote('not voting', member)
            # Parenthetical votes appear to not be counted in the
            # totals for Yea, Nay, _or_ Missed
            elif re.search(r'\([YN]\)', member_vote):
                continue
            else:
                raise ValueError("Unknown vote type found: {}".format(member_vote))

        yield vote


class SubjectPDF(PDF):
    pdftotext_type = 'text-nolayout'

    def handle_page(self):
        """
            sort of a state machine

            after a blank line if there's an all caps phrase that's the new subject

            if a line contains (H|S)(\d+) that bill gets current subject
        """
        subjects = defaultdict(set)

        SUBJ_RE = re.compile('^[A-Z ,()]+$')
        BILL_RE = re.compile('[HS]\d+(?:-[A-Z])?')

        subject = None

        for line in self.lines:
            if SUBJ_RE.match(line):
                subject = line.lower().strip()
            elif subject and BILL_RE.findall(line):
                for bill in BILL_RE.findall(line):
                    # normalize bill id to [SH]#
                    bill = bill.replace('-', '')
                    subjects[bill].add(subject)

        return subjects


class FlBillScraper(Scraper, Spatula):

    def scrape(self, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        subject_url = ('http://www.leg.state.fl.us/data/session/{}/citator/Daily/subindex.pdf'
                       .format(session))
        subjects = self.scrape_page(SubjectPDF, subject_url)

        url = "http://flsenate.gov/Session/Bills/{}?chamber=both".format(session)
        yield from self.scrape_page_items(StartPage, url, session=session, subjects=subjects)
