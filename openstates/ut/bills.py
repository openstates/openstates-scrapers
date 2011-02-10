import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from openstates.ut import metadata

import lxml.html


class UTBillScraper(BillScraper):
    state = 'ut'

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
        with self.urlopen(url) as page:
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
                bill.add_version(name, link.attrib['href'])

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
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for row in page.xpath('//table/tr')[1:]:
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
                elif action == '2nd reading':
                    type = 'bill:reading:2'
                elif action == '3rd reading':
                    type = 'bill:reading:3'
                elif action == 'failed':
                    type = 'bill:failed'
                else:
                    type = 'other'

                bill.add_action(actor, action, date, type=type)

                # Check if this action is a vote
                vote_links = row.xpath('td/font/font/a')
                for vote_link in vote_links:
                    vote_url = vote_link.attrib['href']

                    # Committee votes are of a different format that
                    # we don't handle yet
                    if not vote_url.endswith('txt'):
                        continue

                    self.parse_vote(bill, actor, date, action, vote_url)

    def parse_vote(self, bill, actor, date, motion, url):
        with self.urlopen(url) as page:
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
                        location=vote_location)
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
