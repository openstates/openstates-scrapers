import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html
import scrapelib
import logging

logger = logging.getLogger('openstates')

class UTBillScraper(BillScraper):
    jurisdiction = 'ut'

    def accept_response(self, response):
        # check for rate limit pages
        normal = super(UTBillScraper, self).accept_response(response)
        return (normal and
                'com.microsoft.jdbc.base.BaseSQLException' not in
                    response.text and
                'java.sql.SQLException' not in
                    response.text)
        # The UT site has been throwing a lot of transiant DB errors, these
        # will backoff and retry if their site has an issue. Seems to happen
        # often enough.

    def scrape(self, chamber, session):
        self.validate_session(session)

        if chamber == 'lower':
            bill_abbrs = r'HB|HCR|HJ|HR'
        else:
            bill_abbrs = r'SB|SCR|SJR|SR'

        bill_list_re = r'(%s).*ht\.htm' % bill_abbrs

        bill_list_url = "http://www.le.state.ut.us/~%s/bills.htm" % (
            session.replace(' ', ''))

        with self.urlopen(bill_list_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(bill_list_url)

            for link in page.xpath('//a'):
                if "href" not in link.attrib:
                    continue  # XXX: There are some funky <a> tags here.

                if re.search(bill_list_re, link.attrib['href']):
                    self.scrape_bill_list(chamber, session,
                                          link.attrib['href'])

    def scrape_bill_list(self, chamber, session, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath('//a[contains(@href, "billhtm")]'):
                bill_id = link.xpath('string()').strip()

                self.scrape_bill(chamber, session, bill_id,
                                 link.attrib['href'])

    def scrape_bill(self, chamber, session, bill_id, url):
        try:
            page = self.urlopen(url)
        except scrapelib.HTTPError:
            self.warning("couldn't open %s, skipping bill" % url)
            return
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        header = page.xpath('//h3/br')[0].tail.replace('&nbsp;', ' ')
        title, primary_sponsor = header.split(' -- ')

        if bill_id.startswith('H.B.') or bill_id.startswith('S.B.'):
            bill_type = ['bill']
        elif bill_id.startswith('H.R.') or bill_id.startswith('S.R.'):
            bill_type = ['resolution']
        elif bill_id.startswith('H.C.R.') or bill_id.startswith('S.C.R.'):
            bill_type = ['concurrent resolution']
        elif bill_id.startswith('H.J.R.') or bill_id.startswith('S.J.R.'):
            bill_type = ['joint resolution']

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_sponsor('primary', primary_sponsor)
        bill.add_source(url)

        for link in page.xpath(
            '//a[contains(@href, "bills/") and text() = "HTML"]'):

            name = link.getprevious().tail.strip()
            bill.add_version(name, link.attrib['href'], mimetype="text/html")
            next = link.getnext()
            if next.text == "PDF":
                bill.add_version(name, next.attrib['href'],
                                 mimetype="application/pdf")

        for link in page.xpath(
            "//a[contains(@href, 'fnotes') and text() = 'HTML']"):

            bill.add_document("Fiscal Note", link.attrib['href'])

        subjects = []
        for link in page.xpath("//a[contains(@href, 'RelatedBill')]"):
            subjects.append(link.text.strip())
        bill['subjects'] = subjects

        status_link = page.xpath('//a[contains(@href, "billsta")]')[0]
        self.parse_status(bill, status_link.attrib['href'])

        self.save_bill(bill)

    def parse_status(self, bill, url):
        with self.urlopen(url) as page:
            bill.add_source(url)
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            uniqid = 0

            for row in page.xpath('//table/tr')[1:]:
                uniqid += 1
                date = row.xpath('string(td[1])')
                date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

                action = row.xpath('string(td[2])')
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
                    comm_link = row.xpath("td[3]/font/font/a")[0]
                    comm = re.match(
                        r"writetxt\('(.*)'\)",
                        comm_link.attrib['onmouseover']).group(1)
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

                    # Committee votes are of a different format that
                    # we don't handle yet
                    if not vote_url.endswith('txt'):
                        self.parse_html_vote(bill, actor, date, action,
                                             vote_url, uniqid)
                    else:
                        self.parse_vote(bill, actor, date, action,
                                        vote_url, uniqid)

    def scrape_committee_vote(self, bill, actor, date, motion, url, uniqid):
        with self.urlopen(url) as page:
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
            count = obj.xpath(".//b")[0].tail.replace("-", "").strip()
            count = int(count)
            votes = []
            for vote in obj.xpath(".//br"):
                vote = vote.tail
                if vote:
                    vote = vote.strip()
                    votes.append(vote)
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
        with self.urlopen(url) as page:
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
            logger.warning(descr)
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

        logger.info(vote)
        bill.add_vote(vote)


    def parse_vote(self, bill, actor, date, motion, url, uniqid):
        with self.urlopen(url) as page:
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
