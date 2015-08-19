import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from openstates.utils import LXMLMixin

import lxml.html
import scrapelib


SUB_BLACKLIST = [
    "Second Substitute",
    "Third Substitute",
    "Fourth Substitute",
    "Fifth Substitute",
    "Sixth Substitute",
    "Seventh Substitute",
    "Eighth Substitute",
    "Ninth Substitute",
    "Substitute",
]  # Pages are the same, we'll strip this from bills we catch.


class UTBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'ut'

    def scrape(self, session, chambers):
        self.validate_session(session)

        # Identify the index page for the given session
        sessions = self.lxmlize(
                'http://le.utah.gov/Documents/bills.htm')
        session_search_text = session
        if "s" not in session.lower() and "h" not in session.lower():
            session_search_text += "GS"


        sessions = sessions.xpath(
                '//p/a[contains(@href, "{}")]'.format(session_search_text))
        
        session_url = ''
        for elem in sessions:
            if re.sub(r'\s+', " ", elem.xpath('text()')[0]) == \
                    self.metadata['session_details'][session]['_scraped_name']:
                session_url = elem.xpath('@href')[0]
        assert session_url

        # For some sessions the link doesn't go straight to the bill list
        doc = self.lxmlize(session_url)
        replacement_session_url = doc.xpath('//a[text()="Numbered Bills" and contains(@href, "DynaBill/BillList")]/@href')
        if replacement_session_url:
            (session_url, ) = replacement_session_url

        # Identify all the bill lists linked from a given session's page
        bill_indices = [
                re.sub(r'^r', "", x) for x in
                self.lxmlize(session_url).xpath('//div[contains(@id, "0")]/@id')
                ]

        # Capture the bills from each of the bill lists
        for bill_index in bill_indices:
            if bill_index.startswith("H"):
                chamber = 'lower'
            elif bill_index.startswith("S"):
                chamber = 'upper'
            else:
                raise AssertionError(
                        "Unknown bill type found: {}".format(bill_index))

            bill_index = self.lxmlize(session_url + "&bills=" + bill_index)
            bills = bill_index.xpath('//a[contains(@href, "/bills/static/")]')

            for bill in bills:
                self.scrape_bill(
                        chamber=chamber,
                        session=session,
                        bill_id=bill.xpath('text()')[0],
                        url=bill.xpath('@href')[0]
                        )

    def scrape_bill(self, chamber, session, bill_id, url):
        page = self.lxmlize(url)

        (header, ) = page.xpath('//h3[@class="heading"]/text()')
        title = header.replace(bill_id, "").strip()

        if '.B. ' in bill_id:
            bill_type = 'bill'
        elif bill_id.startswith('H.R. ') or bill_id.startswith('S.R. '):
            bill_type = 'resolution'
        elif '.C.R. ' in bill_id:
            bill_type = 'concurrent resolution'
        elif '.J.R. ' in bill_id:
            bill_type = 'joint resolution'

        for flag in SUB_BLACKLIST:
            if flag in bill_id:
                bill_id = bill_id.replace(flag, " ")
        bill_id = re.sub("\s+", " ", bill_id).strip()

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(url)

        primary_info = page.xpath('//div[@id="billsponsordiv"]')
        for info in primary_info:
            (title, name) = [x.strip() for x
                             in info.xpath('.//text()')
                             if x.strip()]
            assert title == "Bill Sponsor:"
            name = name.replace("Sen. ", "").replace("Rep. ", "")
            bill.add_sponsor('primary', name)

        floor_info = page.xpath('//div[@id="floorsponsordiv"]//text()')
        floor_info = [ x.strip() for x in floor_info if x.strip() ]
        if len(floor_info) in (0, 1):
            # This indicates that no floor sponsor was found
            pass
        elif len(floor_info) == 2:
            assert floor_info[0] == "Floor Sponsor:"
            floor_sponsor = floor_info[1].\
                    replace("Sen. ", "").replace("Rep. ", "")
            bill.add_sponsor('cosponsor', floor_sponsor)
        else:
            raise AssertionError("Unexpected floor sponsor HTML found")

        versions =  page.xpath(
                '//b[text()="Bill Text"]/following-sibling::ul/li/'
                'a[text() and not(text()=" ")]'
                )
        for version in versions:
            bill.add_version(
                    version.xpath('text()')[0].strip(),
                    version.xpath('following-sibling::a[1]/@href')[0],
                    mimetype='application/pdf'
                    )

        for fiscal_link in page.xpath(
            "//input[contains(@value, 'fnotes') and not(contains(@value, ';'))]/@value"):
            bill.add_document("Fiscal Note", fiscal_link)

        subjects = []
        for link in page.xpath("//a[contains(@href, 'RelatedBill')]"):
            subjects.append(link.text.strip())
        bill['subjects'] = subjects

        status_table = page.xpath('//div[@id="billStatus"]//table')[0]
        self.parse_status(bill, status_table)

        self.save_bill(bill)

    def parse_status(self, bill, status_table):
        page = status_table
        uniqid = 0

        for row in page.xpath('tr')[1:]:
            uniqid += 1
            date = row.xpath('string(td[1])')
            date = date.split("(")[0]
            date = datetime.datetime.strptime(date.strip(), "%m/%d/%Y").date()

            action = row.xpath('string(td[2])').strip()
            actor = bill['chamber']

            if '/' in action:
                actor = action.split('/')[0].strip()

                if actor == 'House':
                    actor = 'lower'
                elif actor == 'Senate':
                    actor = 'upper'
                elif actor == 'LFA':
                    actor = 'Office of the Legislative Fiscal Analyst'

                action = '/'.join(action.split('/')[1:]).strip()

            if action == 'Governor Signed':
                actor = 'executive'
                type = 'governor:signed'
            elif action == 'Governor Vetoed':
                actor = 'executive'
                type = 'governor:vetoed'
            elif action.startswith('1st reading'):
                type = ['bill:introduced', 'bill:reading:1']
            elif action == 'to Governor':
                type = 'governor:received'
            elif action == 'passed 3rd reading':
                type = 'bill:passed'
            elif action.startswith('passed 2nd & 3rd readings'):
                type = 'bill:passed'
            elif action == 'to standing committee':
                comm = row.xpath("td[3]/font/text()")[0]
                action = "to " + comm
                type = 'committee:referred'
            elif action.startswith('2nd reading'):
                type = 'bill:reading:2'
            elif action.startswith('3rd reading'):
                type = 'bill:reading:3'
            elif action == 'failed':
                type = 'bill:failed'
            elif action.startswith('2nd & 3rd readings'):
                type = ['bill:reading:2', 'bill:reading:3']
            elif action == 'passed 2nd reading':
                type = 'bill:reading:2'
            elif 'Comm - Favorable Recommendation' in action:
                type = 'committee:passed:favorable'
            elif action == 'committee report favorable':
                type = 'committee:passed:favorable'
            else:
                type = 'other'

            bill.add_action(actor, action, date, type=type,
                            _vote_id=uniqid)

            # Check if this action is a vote
            vote_links = row.xpath('./td[4]//a')
            for vote_link in vote_links:
                vote_url = vote_link.attrib['href']

                if not vote_url.endswith('txt'):
                    self.parse_html_vote(bill, actor, date, action,
                                         vote_url, uniqid)
                else:
                    self.parse_vote(bill, actor, date, action,
                                    vote_url, uniqid)

    def scrape_committee_vote(self, bill, actor, date, motion, url, uniqid):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        committee = page.xpath("//b")[0].text_content()
        votes = page.xpath("//table")[0]
        rows = votes.xpath(".//tr")[0]
        yno = rows.xpath(".//td")
        if len(yno) < 3:
            yes = yno[0]
            no, other = None, None
        else:
            yes, no, other = rows.xpath(".//td")

        def proc_block(obj):
            if obj is None:
                return {
                    "type": None,
                    "count": None,
                    "votes": []
                }

            typ = obj.xpath("./b")[0].text_content()
            votes = []
            for vote in obj.xpath(".//br"):
                if vote.tail:
                    vote = vote.tail.strip()
                    if vote:
                        votes.append(vote)
            count = len(votes)
            return {
                "type": typ,
                "count": count,
                "votes": votes
            }

        vote_dict = {
            "yes": proc_block(yes),
            "no": proc_block(no),
            "other": proc_block(other),
        }

        yes_count = vote_dict['yes']['count']
        no_count = vote_dict['no']['count'] or 0
        other_count = vote_dict['other']['count'] or 0

        vote = Vote(
            actor,
            date,
            motion,
            (yes_count > no_count),
            yes_count,
            no_count,
            other_count,
            _vote_id=uniqid)
        vote.add_source(url)

        for key in vote_dict:
            for voter in vote_dict[key]['votes']:
                getattr(vote, key)(voter)

        bill.add_vote(vote)

    def parse_html_vote(self, bill, actor, date, motion, url, uniqid):
        try:
            page = self.get(url).text
        except scrapelib.HTTPError:
            self.warning("A vote page not found for bill {}".
                         format(bill['bill_id']))
            return
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        descr = page.xpath("//b")[0].text_content()

        if "on voice vote" in descr:
            return

        if "committee" in descr.lower():
            return self.scrape_committee_vote(
                bill, actor, date, motion, url, uniqid
            )

        passed = None

        if "Passed" in descr:
            passed = True
        elif "Failed" in descr:
            passed = False
        elif "UTAH STATE LEGISLATURE" in descr:
            return
        else:
            self.warning(descr)
            raise NotImplemented("Can't see if we passed or failed")

        headings = page.xpath("//b")[1:]
        votes = page.xpath("//table")
        sets = zip(headings, votes)
        vdict = {}
        for (typ, votes) in sets:
            txt = typ.text_content()
            arr = [x.strip() for x in txt.split("-", 1)]
            if len(arr) != 2:
                continue
            v_txt, count = arr
            v_txt = v_txt.strip()
            count = int(count)
            people = [x.text_content().strip() for x in
                      votes.xpath(".//font[@face='Arial']")]

            vdict[v_txt] = {
                "count": count,
                "people": people
            }

        vote = Vote(actor, date,
                    motion,
                    passed,
                    vdict['Yeas']['count'],
                    vdict['Nays']['count'],
                    vdict['Absent or not voting']['count'],
                    _vote_id=uniqid)
        vote.add_source(url)

        for person in vdict['Yeas']['people']:
            vote.yes(person)
        for person in vdict['Nays']['people']:
            vote.no(person)
        for person in vdict['Absent or not voting']['people']:
            vote.other(person)

        self.info("Adding vote to bill")
        bill.add_vote(vote)

    def parse_vote(self, bill, actor, date, motion, url, uniqid):
        page = self.get(url).text
        bill.add_source(url)
        vote_re = re.compile('YEAS -?\s?(\d+)(.*)NAYS -?\s?(\d+)'
                             '(.*)ABSENT( OR NOT VOTING)? -?\s?'
                             '(\d+)(.*)',
                             re.MULTILINE | re.DOTALL)
        match = vote_re.search(page)
        yes_count = int(match.group(1))
        no_count = int(match.group(3))
        other_count = int(match.group(6))

        if yes_count > no_count:
            passed = True
        else:
            passed = False

        if actor == 'upper' or actor == 'lower':
            vote_chamber = actor
            vote_location = ''
        else:
            vote_chamber = ''
            vote_location = actor

        vote = Vote(vote_chamber, date,
                    motion, passed, yes_count, no_count,
                    other_count,
                    location=vote_location,
                    _vote_id=uniqid)
        vote.add_source(url)

        yes_votes = re.split('\s{2,}', match.group(2).strip())
        no_votes = re.split('\s{2,}', match.group(4).strip())
        other_votes = re.split('\s{2,}', match.group(7).strip())

        for yes in yes_votes:
            if yes:
                vote.yes(yes)
        for no in no_votes:
            if no:
                vote.no(no)
        for other in other_votes:
            if other:
                vote.other(other)

        bill.add_vote(vote)
