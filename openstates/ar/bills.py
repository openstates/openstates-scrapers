import re
import csv
import StringIO
import datetime
import collections

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


class ARBillScraper(BillScraper):
    state = 'ar'

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)

        self.bills = {}
        self.scrape_bill(chamber, session)
        self.scrape_actions()

        for bill in self.bills.itervalues():
            self.save_bill(bill)

    def scrape_bill(self, chamber, session):
        url = "ftp://www.arkleg.state.ar.us/dfadooas/LegislativeMeasures.txt"
        page = self.urlopen(url).decode('latin-1')
        page = unicode_csv_reader(StringIO.StringIO(page), delimiter='|')

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
                'MR': 'memorial resolution',
                'CMR': 'concurrent memorial resolution'}[type_spec]

            bill = Bill('2011', chamber, bill_id, row[3], type=bill_type)
            bill.add_source(url)
            bill.add_sponsor('lead sponsor', row[11])

            version_url = ("ftp://www.arkleg.state.ar.us/Bills/"
                           "%s/Public/%s.pdf" % (
                               session, bill_id.replace(' ', '')))
            bill.add_version(bill_id, version_url)

            self.scrape_votes(bill)

            self.bills[bill_id] = bill

    def scrape_actions(self):
        url = "ftp://www.arkleg.state.ar.us/dfadooas/ChamberActions.txt"
        page = self.urlopen(url)
        page = csv.reader(StringIO.StringIO(page))

        for row in page:
            bill_id = "%s%s %s" % (row[1], row[2], row[3])
            if bill_id not in self.bills:
                continue

            # Commas aren't escaped, but only one field (the action) can
            # contain them so we can work around it by using both positive
            # and negative offsets
            bill_id = "%s%s %s" % (row[1], row[2], row[3])
            actor = {'HU': 'lower', 'SU': 'upper'}[row[-5].upper()]
            date = datetime.datetime.strptime(row[6], "%Y-%m-%d %H:%M:%S")
            action = ','.join(row[7:-5])

            action_type = []
            if action.startswith('Filed'):
                action_type.append('bill:introduced')
            elif (action.startswith('Read first time') or
                  action.startswith('Read the first time')):
                action_type.append('bill:reading:1')
            if re.match('Read the first time, .*, read the second time'):
                action_type.append('bill:reading:2')
            elif action.startswith('Read the third time'):
                action_type.append('bill:reading:3')
                if action.endswith('and passed.'):
                    action_type.append('bill:passed')
            elif action.startswith('DELIVERED TO GOVERNOR'):
                action_type.append('governor:received')

            if 'referred to' in action:
                action_type.append('committee:referred')

            if 'Returned by the Committee' in action:
                if 'recommendation that it Do Pass' in action:
                    action_type.append('committee:passed:favorable')
                else:
                    action_type.append('committee:passed')

            self.bills[bill_id].add_action(actor, action, date,
                                           type=action_type or ['other'])

    def scrape_votes(self, bill):
        # We need to scrape each bill page in order to grab associated votes.
        # It's still more efficient to get the rest of the data we're
        # interested in from the CSVs, though, because their site splits
        # other info (e.g. actions) across many pages
        measureno = bill['bill_id'].replace(' ', '')
        url = ("http://www.arkleg.state.ar.us/assembly/2011/2011R/"
               "Pages/BillInformation.aspx?measureno=%s" % measureno)
        bill.add_source(url)

        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Votes.aspx')]"):
            date = link.xpath("string(../../td[2])")
            date = datetime.datetime.strptime(date, "%m/%d/%Y %I:%M:%S %p")

            motion = link.xpath("string(../../td[3])")

            self.scrape_vote(bill, date, motion, link.attrib['href'])

    def scrape_vote(self, bill, date, motion, url):
        page = lxml.html.fromstring(self.urlopen(url))

        if url.endswith('Senate'):
            actor = 'upper'
        else:
            actor = 'lower'

        count_path = "string(//td[@align = 'center' and contains(., '%s: ')])"
        yes_count = int(page.xpath(count_path % "Yeas").split()[-1])
        no_count = int(page.xpath(count_path % "Nays").split()[-1])
        other_count = int(page.xpath(count_path % "Non Voting").split()[-1])
        other_count += int(page.xpath(count_path % "Present").split()[-1])

        passed = yes_count > no_count + other_count
        vote = Vote(actor, date, motion, passed, yes_count,
                    no_count, other_count)
        vote.add_source(url)

        vote_path = "//h3[. = '%s']/following-sibling::table[1]/tr/td/a"
        for yes in page.xpath(vote_path % "Yeas"):
            vote.yes(yes.text)
        for no in page.xpath(vote_path % "Nays"):
            vote.no(no.text)
        for other in page.xpath(vote_path % "Non Voting"):
            vote.other(other.text)
        for other in page.xpath(vote_path % "Present"):
            vote.other(other.text)

        bill.add_vote(vote)
