import os
import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf
import lxml.html

from openstates.utils import LXMLMixin


class FLBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'fl'
    CHAMBERS = {'H': 'lower', 'S': 'upper'}

    def scrape(self, session, chambers):
        session_number = self.get_session_number(session)
        self.validate_session(session)
        url = "http://flsenate.gov/Session/Bills/{}?chamber=both".format(
            session)

        page = self.lxmlize(url)
        try:
            page_count = int(page.xpath(
                "//a[contains(., 'Next')][1]/preceding::a[1]/text()")[0])
        except IndexError:
            if not page.xpath('//div[@class="ListPagination"]/span'):
                raise AssertionError("No bills found for the session")
            elif set(page.xpath('//div[@class="ListPagination"]/span/text()')) != set(["1"]):
                raise AssertionError("Bill list pagination needed but not used")
            else:
                self.warning(
                    "Pagination not used; "
                    "make sure there're only a few bills for this session")
            page_count = 1

        for page_number in range(1, page_count + 1):
            page_url = (url + '&PageNumber={}'.format(page_number))
            page = self.lxmlize(page_url)

            link_path = "//a[contains(@href, '/Session/Bill/{}/')]".format(
                session)
            for link in page.xpath(link_path):
                bill_id = link.text.strip()
                title = link.xpath(
                    "string(../following-sibling::td[1])").strip()
                sponsor = link.xpath(
                    "string(../following-sibling::td[2])").strip()
                bill_url = link.attrib['href'] + '/ByCategory'
                self.scrape_bill(session, session_number,
                                 bill_id, title, sponsor, bill_url)

    def accept_response(self, response):
        normal = super(FLBillScraper, self).accept_response(response)
        bill_check = True
        text_check = True

        if not response.url.lower().endswith('pdf'):
            if response.url.startswith("http://flsenate.gov/Session/Bill/20"):
                bill_check = "tabBodyVoteHistory" in response.text

            text_check = (
                'he page you have requested has encountered an error.'
                not in response.text)

        valid = (normal and
                 bill_check and
                 text_check)
        if not valid:
            raise Exception('Response was invalid')
        return valid

    def scrape_bill(self, session, session_number, bill_id, title, sponsor,
                    url):
        try:
            html = self.get(url).text
        except:
            return
        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        bill = Bill(session, self.CHAMBERS[bill_id[0]], bill_id, title)
        bill.add_source(url)

        sponsor = re.sub(r'^(?:Rep|Sen)\.\s', "", sponsor)
        bill.add_sponsor('primary', sponsor)

        hist_table = page.xpath(
            "//div[@id = 'tabBodyBillHistory']//table")[0]

        if bill_id.startswith('SB ') or \
                bill_id.startswith('HB ') or \
                bill_id.startswith('SPB ') or \
                bill_id.startswith('HPB '):
            bill_type = 'bill'
        elif bill_id.startswith('HR ') or bill_id.startswith('SR '):
            bill_type = 'resolution'
        elif bill_id.startswith('HJR ') or bill_id.startswith('SJR '):
            bill_type = 'joint resolution'
        elif bill_id.startswith('SCR ') or bill_id.startswith('HCR '):
            bill_type = 'concurrent resolution'
        elif bill_id.startswith('SM ') or bill_id.startswith('HM '):
            bill_type = 'memorial'
        else:
            raise Exception('Failed to identify bill type.')

        bill['type'] = [bill_type]

        for tr in hist_table.xpath("tbody/tr"):
            date = tr.xpath("string(td[1])")
            date = datetime.datetime.strptime(
                date, "%m/%d/%Y").date()

            actor = tr.xpath("string(td[2])")
            actor = {'Senate': 'upper', 'House': 'lower'}.get(
                actor, actor)

            act_text = tr.xpath("string(td[3])").strip()
            for action in act_text.split(u'\u2022'):
                action = action.strip()
                if not action:
                    continue

                action = re.sub(r'-(H|S)J\s+(\d+)$', '',
                                action)

                atype = []
                if action.startswith('Referred to'):
                    atype.append('committee:referred')
                elif action.startswith('Favorable by'):
                    atype.append('committee:passed')
                elif action == "Filed":
                    atype.append("bill:filed")
                elif action.startswith("Withdrawn"):
                    atype.append("bill:withdrawn")
                elif action.startswith("Died"):
                    atype.append("bill:failed")
                elif action.startswith('Introduced'):
                    atype.append('bill:introduced')
                elif action.startswith('Read 2nd time'):
                    atype.append('bill:reading:2')
                elif action.startswith('Read 3rd time'):
                    atype.append('bill:reading:3')
                elif action.startswith('Adopted'):
                    atype.append('bill:passed')
                elif action.startswith('CS passed'):
                    atype.append('bill:passed')
                elif action.startswith('Chapter No'):
                    actor = 'executive'
                elif action.startswith('Signed by Officers'):
                    atype.append('governor:received')
                    actor = 'governor'
                elif action.startswith('Approved by Gov'):
                    atype.append('governor:signed')
                    actor = 'governor'
                elif action.startswith('Vetoed by Gov'):
                    atype.append('governor:vetoed')
                    actor = 'governor'
                elif action.startswith('Became Law, Governor\'s Veto notwithstanding'):
                    atype.append("bill:veto_override:passed")
                    #Veto overrides are rare in FL, so this is a guess, based on
                    #http://archive.flsenate.gov/Session/index.cfm?Mode=Bills&SubMenu=1&Tab=session&BI_Mode=ViewBillInfo&BillNum=1565&Chamber=Senate&Year=2010

                if not actor:
                    self.logger.warning("%s action %s missing actor." % (bill_id, action))

                bill.add_action(actor, action, date, type=atype)

        try:
            version_table = page.xpath(
                "//div[@id = 'tabBodyBillText']/table")[0]
            for tr in version_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                version_url = tr.xpath("td/a[1]")[0].attrib['href']
                if version_url.endswith('PDF'):
                    mimetype = 'application/pdf'
                elif version_url.endswith('HTML'):
                    mimetype = 'text/html'
                bill.add_version(name, version_url, mimetype=mimetype)
        except IndexError:
            self.log("No version table for %s" % bill_id)

        try:
            analysis_table = page.xpath(
                "//div[@id = 'tabBodyAnalyses']/table")[0]
            for tr in analysis_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                name += " -- " + tr.xpath("string(td[3])").strip()
                name = re.sub(r'\s+', " ", name)
                date = tr.xpath("string(td[4])").strip()
                if date:
                    name += " (%s)" % date
                analysis_url = tr.xpath("td/a")[0].attrib['href']
                bill.add_document(name, analysis_url)
        except IndexError:
            self.log("No analysis table for %s" % bill_id)

        vote_tables = page.xpath(
            "//div[@id = 'tabBodyVoteHistory']//table")

        for vote_table in vote_tables:
            for tr in vote_table.xpath("tbody/tr"):
                vote_date = tr.xpath("string(td[3])").strip()
                if vote_date.isalpha():
                    vote_date = tr.xpath("string(td[2])").strip()
                try:
                    vote_date = datetime.datetime.strptime(
                        vote_date, "%m/%d/%Y %H:%M %p").date()
                except ValueError:
                    msg = 'Got bogus vote date: %r'
                    self.logger.warning(msg % vote_date)

                vote_url = tr.xpath("td[4]/a")[0].attrib['href']
                if "SenateVote" in vote_url:
                    self.scrape_floor_vote('upper', bill, vote_date, vote_url)
                elif "HouseVote" in vote_url:
                    self.scrape_floor_vote('lower', bill, vote_date, vote_url)
                else:
                    self.scrape_uppper_committee_vote(
                        bill, vote_date, vote_url)
        else:
            self.log("No vote table for %s" % bill_id)

        self.scrape_lower_committee_votes(session_number, bill)

        self.save_bill(bill)

    def scrape_uppper_committee_vote(self, bill, date, url):
        (path, resp) = self.urlretrieve(url)
        text = convert_pdf(path, 'text')
        lines = text.split("\n")
        os.remove(path)

        (_, motion) = lines[5].split("FINAL ACTION:")
        motion = motion.strip()
        if not motion:
            self.warning("Vote appears to be empty")
            return

        vote_top_row = [
            lines.index(x) for x in lines if
            re.search(r'^\s+Yea\s+Nay.*?(?:\s+Yea\s+Nay)+$', x)][0]
        yea_columns_end = lines[vote_top_row].index("Yea") + len("Yea")
        nay_columns_begin = lines[vote_top_row].index("Nay")

        votes = {'yes': [], 'no': [], 'other': []}
        for line in lines[(vote_top_row + 1):]:
            if line.strip():
                member = re.search(r'''(?x)
                        ^\s+(?:[A-Z\-]+)?\s+  # Possible vote indicator
                        ([A-Z][a-z]+  # Name must have lower-case characters
                        [\w\-\s]+)  # Continue looking for the rest of the name
                        (?:,[A-Z\s]+?)?  # Leadership has an all-caps title
                        (?:\s{2,}.*)?  # Name ends when many spaces are seen
                        ''', line).group(1)
                # Usually non-voting members won't even have a code listed
                # Only a couple of codes indicate an actual vote:
                # "VA" (vote after roll call) and "VC" (vote change)
                did_vote = bool(
                    re.search(r'^\s+(X|VA|VC)\s+[A-Z][a-z]', line))
                if did_vote:
                    # Check where the "X" or vote code is on the page
                    vote_column = len(line) - len(line.lstrip())
                    if vote_column <= yea_columns_end:
                        votes['yes'].append(member)
                    elif vote_column >= nay_columns_begin:
                        votes['no'].append(member)
                    else:
                        raise AssertionError(
                            "Unparseable vote found for {0} in {1}:\n{2}".
                            format(member, url, line))
                else:
                    votes['other'].append(member)

            # End loop as soon as no more members are found
            else:
                break

        totals = re.search(
            r'(?msu)\s+(\d{1,3})\s+(\d{1,3})\s+.*?TOTALS', text).groups()
        yes_count = int(totals[0])
        no_count = int(totals[1])
        passed = (yes_count > no_count)
        other_count = len(votes['other'])

        vote = Vote('upper', date, motion, passed, yes_count, no_count,
                    other_count)
        vote.add_source(url)
        vote['yes_votes'] = votes['yes']
        vote['no_votes'] = votes['no']
        vote['other_votes'] = votes['other']

        vote.validate()
        bill.add_vote(vote)

    def scrape_floor_vote(self, chamber, bill, date, url):
        (path, resp) = self.urlretrieve(url)
        text = convert_pdf(path, 'text')
        lines = text.split("\n")
        os.remove(path)

        MOTION_INDEX = 4
        TOTALS_INDEX = 6
        VOTE_START_INDEX = 9

        motion = lines[MOTION_INDEX].strip()
        # Sometimes there is no motion name, only "Passage" in the line above
        if (not motion and
                not lines[MOTION_INDEX - 1].startswith("Calendar Page:")):
            motion = lines[MOTION_INDEX - 1]
            MOTION_INDEX -= 1
            TOTALS_INDEX -= 1
            VOTE_START_INDEX -= 1
        else:
            assert motion, "Floor vote's motion name appears to be empty"

        for _extra_motion_line in range(2):
            MOTION_INDEX += 1
            if lines[MOTION_INDEX].strip():
                motion = "{}, {}".format(motion, lines[MOTION_INDEX].strip())
                TOTALS_INDEX += 1
                VOTE_START_INDEX += 1
            else:
                break

        (yes_count, no_count, other_count) = [int(x) for x in re.search(
            r'^\s+Yeas - (\d+)\s+Nays - (\d+)\s+Not Voting - (\d+)\s*$',
            lines[TOTALS_INDEX]).groups()]
        passed = (yes_count > no_count)

        vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                    other_count)
        vote.add_source(url)

        for line in lines[VOTE_START_INDEX:]:
            if not line.strip():
                break

            if " President " in line:
                line = line.replace(" President ", " ")
            elif " Speaker " in line:
                line = line.replace(" Speaker ", " ")

            # Votes follow the pattern of:
            # [vote code] [member name]-[district number]
            for member in re.findall(r'\s*Y\s+(.*?)-\d{1,3}\s*', line):
                vote.yes(member)
            for member in re.findall(r'\s*N\s+(.*?)-\d{1,3}\s*', line):
                vote.no(member)
            for member in re.findall(r'\s*(?:EX|AV)\s+(.*?)-\d{1,3}\s*', line):
                vote.other(member)

        try:
            vote.validate()
        except ValueError:
            # On a rare occasion, a member won't have a vote code,
            # which indicates that they didn't vote. The totals reflect
            # this.
            self.logger.info("Votes don't add up; looking for additional ones")
            for line in lines[VOTE_START_INDEX:]:
                if not line.strip():
                    break
                for member in re.findall(
                        r'\s{8,}([A-Z][a-z\'].*?)-\d{1,3}', line):
                    vote.other(member)

        vote.validate()
        bill.add_vote(vote)

    def get_session_number(self, session):
        '''
        The House uses a session number in its forms, so need to be
        able to ascertain this from the session name
        '''

        session_number = None

        house_url = 'http://www.myfloridahouse.gov/Sections/Bills/bills.aspx'
        doc = self.lxmlize(house_url)
        session_options = doc.xpath('//select[@id="ddlSession"]/option')
        for option in session_options:

            option_name = option.text_content().strip()
            option_slug = option_name.split(' ')[-1]
            if option_slug == session:
                assert session_number is None, "Multiple sessions found"
                session_number = option.attrib['value']

        return session_number

    def scrape_lower_committee_votes(self, session_number, bill):
        '''
        House committee roll calls are not available on the Senate's
        website. Furthermore, the House uses an internal ID system in
        its URLs, making accessing those pages non-trivial.

        This function will fetch all the House committee votes for the
        given bill, and add the votes to that object.
        '''

        house_url = 'http://www.myfloridahouse.gov/Sections/Bills/bills.aspx'

        # Keep the digits and all following characters in the bill's ID
        bill_number = re.search(r'^\w+\s(\d+\w*)$', bill['bill_id']).group(1)

        form = {
            'rblChamber': 'B',
            'ddlSession': session_number,
            'ddlBillList': '-1',
            'txtBillNumber': bill_number,
            'ddlSponsor': '-1',
            'ddlReferredTo': '-1',
            'SubmittedByControl': '',
        }
        doc = lxml.html.fromstring(self.post(url=house_url, data=form).text)
        doc.make_links_absolute(house_url)

        (bill_link, ) = doc.xpath(
            '//a[contains(@href, "/Bills/billsdetail.aspx?BillId=")]/@href')
        bill_doc = self.lxmlize(bill_link)
        links = bill_doc.xpath('//a[text()="See Votes"]/@href')

        for link in links:
            vote_doc = self.lxmlize(link)

            (date, ) = vote_doc.xpath(
                '//span[@id="ctl00_ContentPlaceHolder1_lblDate"]/text()')
            date = datetime.datetime.strptime(
                date, '%m/%d/%Y %I:%M:%S %p').date()

            totals = vote_doc.xpath('//table//table')[-1].text_content()
            totals = re.sub(r'(?mu)\s+', " ", totals).strip()
            (yes_count, no_count, other_count) = [int(x) for x in re.search(
                r'(?m)Total Yeas:\s+(\d+)\s+Total Nays:\s+(\d+)\s+'
                'Total Missed:\s+(\d+)', totals).groups()]
            passed = yes_count > no_count

            (committee, ) = vote_doc.xpath(
                '//span[@id="ctl00_ContentPlaceHolder1_lblCommittee"]/text()')
            (action, ) = vote_doc.xpath(
                '//span[@id="ctl00_ContentPlaceHolder1_lblAction"]/text()')
            motion = "{} ({})".format(action, committee)

            vote = Vote('lower', date, motion, passed, yes_count, no_count,
                        other_count)
            vote.add_source(link)

            for member_vote in vote_doc.xpath('//table//table//table//td'):
                if not member_vote.text_content().strip():
                    continue

                (member, ) = member_vote.xpath('span[2]//text()')
                (member_vote, ) = member_vote.xpath('span[1]//text()')

                if member_vote == "Y":
                    vote.yes(member)
                elif member_vote == "N":
                    vote.no(member)
                elif member_vote == "-":
                    vote.other(member)
                # Parenthetical votes appear to not be counted in the
                # totals for Yea, Nay, _or_ Missed
                elif re.search(r'\([YN]\)', member_vote):
                    continue
                else:
                    raise IndexError("Unknown vote type found: {}".format(
                        member_vote))

            vote.validate()
            bill.add_vote(vote)
