import re
import csv
from io import StringIO
import datetime
import pytz
from pupa.scrape import Scraper, Bill, VoteEvent

import lxml.html

TIMEZONE = pytz.timezone('US/Central')


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(unicode_csv_data,
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [cell for cell in row]


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


class ARBillScraper(Scraper):

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)
        chambers = [chamber] if chamber else ['upper', 'lower']
        self.bills = {}

        self.slug = session+'R'

        for Chamber in chambers:
            yield from self.scrape_bill(Chamber, session)
        self.scrape_actions()
        for bill_id, bill in self.bills.items():
            yield bill

    def scrape_bill(self, chamber, session):
        url = "ftp://www.arkleg.state.ar.us/dfadooas/LegislativeMeasures.txt"
        page = self.get(url).text
        page = unicode_csv_reader(StringIO(page), delimiter='|')

        for row in page:
            bill_chamber = {'H': 'lower', 'S': 'upper'}[row[0]]

            if bill_chamber != chamber:
                continue
            bill_id = "%s%s %s" % (row[0], row[1], row[2])

            type_spec = re.match(r'(H|S)([A-Z]+)\s', bill_id).group(2)
            bill_type = {
                'B': 'bill',
                'R': 'resolution',
                'JR': 'joint resolution',
                'CR': 'concurrent resolution',
                'MR': 'memorial',
                'CMR': 'concurrent memorial'}[type_spec]

            if row[-1] != self.slug:
                continue

            bill = Bill(bill_id, legislative_session=session,
                        chamber=chamber, title=row[3], classification=bill_type)
            bill.add_source(url)

            primary = row[11]
            if not primary:
                primary = row[12]

            if primary:
                bill.add_sponsorship(primary, classification='primary',
                                     entity_type='person', primary=True)
            # ftp://www.arkleg.state.ar.us/Bills/
            # TODO: Keep on eye on this post 2017 to see if they apply R going forward.
            session_code = '2017R' if session == '2017' else session

            version_url = ("ftp://www.arkleg.state.ar.us/Bills/"
                           "%s/Public/%s.pdf" % (
                               session_code, bill_id.replace(' ', '')))
            bill.add_version_link(bill_id, version_url, media_type='application/pdf')

            yield from self.scrape_bill_page(bill)

            self.bills[bill_id] = bill

    def scrape_actions(self):
        url = "ftp://www.arkleg.state.ar.us/dfadooas/ChamberActions.txt"
        page = self.get(url).text
        page = csv.reader(StringIO(page))

        for row in page:
            bill_id = "%s%s %s" % (row[1], row[2], row[3])

            if bill_id not in self.bills:
                continue
            # different term
            if row[-2] != self.slug:
                continue

            # Commas aren't escaped, but only one field (the action) can
            # contain them so we can work around it by using both positive
            # and negative offsets
            bill_id = "%s%s %s" % (row[1], row[2], row[3])
            actor = {'HU': 'lower', 'SU': 'upper'}[row[-5].upper()]
            # manual fix for crazy time value
            row[6] = row[6].replace('.520000000', '')

            date = TIMEZONE.localize(datetime.datetime.strptime(row[6], "%Y-%m-%d %H:%M:%S"))
            date = "{:%Y-%m-%d}".format(date)
            action = ','.join(row[7:-5])

            action_type = []
            if action.startswith('Filed'):
                action_type.append('introduction')
            elif (action.startswith('Read first time') or
                  action.startswith('Read the first time')):
                action_type.append('reading-1')
            if re.match('Read the first time, .*, read the second time', action):
                action_type.append('reading-2')
            elif action.startswith('Read the third time and passed'):
                action_type.append('passage')
                action_type.append('reading-3')
            elif action.startswith('Read the third time'):
                action_type.append('reading-3')
            elif action.startswith('DELIVERED TO GOVERNOR'):
                action_type.append('executive-receipt')
            elif action.startswith('Notification'):
                action_type.append('executive-signature')

            if 'referred to' in action:
                action_type.append('referral-committee')

            if 'Returned by the Committee' in action:
                if 'recommendation that it Do Pass' in action:
                    action_type.append('committee-passage-favorable')
                else:
                    action_type.append('committee-passage')

            if re.match(r'Amendment No\. \d+ read and adopted', action):
                action_type.append('amendment-introduction')
                action_type.append('amendment-passage')

            if not action:
                action = '[No text provided]'
            self.bills[bill_id].add_action(action, date, chamber=actor, classification=action_type)

    def scrape_bill_page(self, bill):
        # We need to scrape each bill page in order to grab associated votes.
        # It's still more efficient to get the rest of the data we're
        # interested in from the CSVs, though, because their site splits
        # other info (e.g. actions) across many pages
        try:

            term_year = '2017'
            measureno = bill.identifier.replace(" ", "")
            url = ("http://www.arkleg.state.ar.us/assembly/%s/%s/"
                   "Pages/BillInformation.aspx?measureno=%s" % (
                       term_year, self.slug, measureno))
            page = self.get(url).text
            bill.add_source(url)
            page = lxml.html.fromstring(page)
            for link in page.xpath("//a[contains(@href, 'Amendments')]"):
                num = link.xpath("string(../../td[2])")
                name = "Amendment %s" % num
                bill.add_document_link(name, link.attrib['href'])

            try:
                cosponsor_link = page.xpath(
                    "//a[contains(@href, 'CoSponsors')]")[0]
                self.scrape_cosponsors(bill, cosponsor_link.attrib['href'])
            except IndexError:
                # No cosponsor link is OK
                pass

            for link in page.xpath("//a[contains(@href, 'votes.aspx')]"):
                date = link.xpath("string(../../td[2])")
                date = TIMEZONE.localize(datetime.datetime.strptime(date, "%m/%d/%Y %I:%M:%S %p"))

                motion = link.xpath("string(../../td[3])")
                print("base1")
                yield from self.scrape_vote(bill, date, motion, link.attrib['href'])
        except:
            pass

    def scrape_vote(self, bill, date, motion, url):
        print("called")
        try:
            page = self.get(url).text
            if 'not yet official' in page:
                # Sometimes they link to vote pages before they go live
                pass

            else:
                page = lxml.html.fromstring(page)

                if url.endswith('Senate'):
                    actor = 'upper'
                else:
                    actor = 'lower'

                votevals = ['yes', 'no', 'not voting',  'other']
                count_path = "string(//td[@align = 'center' and contains(., '%s: ')])"
                yes_count = int(page.xpath(count_path % "Yeas").split()[-1])
                no_count = int(page.xpath(count_path % "Nays").split()[-1])
                not_voting_count = int(page.xpath(count_path % "Non Voting").split()[-1])
                other_count = int(page.xpath(count_path % "Present").split()[-1])
                passed = yes_count > no_count + not_voting_count + other_count
                vote = VoteEvent(start_date='2017-03-04', motion_text=motion,
                                 result='pass' if passed else 'fail',
                                 classification='passage',
                                 chamber=actor,
                                 bill=bill)
                try:
                    excused_count = int(page.xpath(count_path % "Excused").split()[-1])
                    vote.set_count('excused', excused_count)
                    votevals.append('excused')
                except:
                    pass
                vote.set_count('yes', yes_count)
                vote.set_count('no', no_count)
                vote.set_count('not voting', not_voting_count)
                vote.set_count('other', other_count)
                vote.add_source(url)

                xpath = (
                    '//*[contains(@class, "ms-standardheader")]/'
                    'following-sibling::table')
                divs = page.xpath(xpath)

                for (voteval, div) in zip(votevals, divs):
                    for a in div.xpath('.//a'):
                        name = a.text_content().strip()
                        if not name:
                            continue
                        else:
                            vote.vote(voteval, name)
                yield vote
        except:
            # sometiems the link is there but is dead
            pass

    def scrape_cosponsors(self, bill, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
