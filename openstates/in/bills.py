import os
import re
import datetime
from collections import defaultdict

import scrapelib
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf
from billy.importers.bills import fix_bill_id

import pytz
import lxml.html

from .actions import Categorizer
from .models import PDFHouseVote


def parse_vote_count(s):
    if s == 'NONE':
        return 0
    return int(s)


def insert_specific_votes(vote, specific_votes):
    for name, vtype in specific_votes:
        if vtype == 'yes':
            vote.yes(name)
        elif vtype == 'no':
            vote.no(name)
        elif vtype == 'other':
            vote.other(name)


def check_vote_counts(vote):
    try:
        assert vote['yes_count'] == len(vote['yes_votes'])
        assert vote['no_count'] == len(vote['no_votes'])
        assert vote['other_count'] == len(vote['other_votes'])
    except AssertionError:
        pass


class INBillScraper(BillScraper):
    jurisdiction = 'in'

    categorizer = Categorizer()

    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        self.build_subject_mapping(session)

        bill_types = {
            'B': ("http://www.in.gov/apps/lsa/session/billwatch/billinfo"
                  "?year=%s&session=1&request=all" % session),
            'JR': ("http://www.in.gov/apps/lsa/session/billwatch/billinfo?"
                   "year=%s&session=1&request=getJointResolutions" % session),
            'CR': ("http://www.in.gov/apps/lsa/session/billwatch/billinfo?year"
                   "=%s&session=1&request=getConcurrentResolutions" % session),
            'R': ("http://www.in.gov/apps/lsa/session/billwatch/billinfo?year="
                  "%s&session=1&request=getSimpleResolutions" % session)
        }

        for type, url in bill_types.iteritems():
            html = self.urlopen(url)
            page = lxml.html.fromstring(html)
            page.make_links_absolute(url)

            abbrev = {'upper': 'S', 'lower': 'H'}[chamber] + type
            xpath = "//a[contains(@href, 'doctype=%s')]" % abbrev
            for link in page.xpath(xpath):
                bill_id = link.text.strip()

                short_title = link.tail.split(' -- ')[1].strip()

                if not short_title:
                    msg = 'Bill %r has no title; skipping.'
                    self.logger.warning(msg % bill_id)
                    continue
                self.scrape_bill(session, chamber, bill_id, short_title,
                                 link.attrib['href'])

    def scrape_bill(self, session, chamber, bill_id, short_title, url):

        try:
            page = self.urlopen(url)
        except scrapelib.HTTPError:
            self.logger.warning('500 error at: %r' % url)
            return
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        # check for Bill Withdrawn header
        h1text = page.xpath('//h1/text()')
        if h1text and h1text[0] == 'Bill Withdrawn':
            return

        title = page.xpath("//br")[8].tail
        if not title:
            title = short_title
        title = title.strip()

        abbrev = bill_id.split()[0]
        if abbrev.endswith('B'):
            bill_type = ['bill']
        elif abbrev.endswith('JR'):
            bill_type = ['joint resolution']
        elif abbrev.endswith('CR'):
            bill_type = ['concurrent resolution']
        elif abbrev.endswith('R'):
            bill_type = ['resolution']

        bill = Bill(session, chamber, bill_id, title,
                    type=bill_type)
        bill.add_source(url)

        action_link = page.xpath("//a[contains(@href, 'getActions')]")[0]
        self.scrape_actions(bill, action_link.attrib['href'])

        version_path = "//a[contains(., '%s')]"
        for version_type in ('Introduced Bill', 'House Bill',
                             'Senate Bill', 'Engrossed Bill',
                             'Enrolled Act'):
            path = version_path % version_type
            links = page.xpath(path)
            if links:

                _url = links[0].attrib['href']

                # Set the mimetype.
                if 'pdf' in _url:
                    mimetype = 'application/pdf'
                else:
                    mimetype = 'text/html'

                bill.add_version(version_type, _url, mimetype=mimetype)

        for vote_link in page.xpath("//a[contains(@href, 'Srollcal')]"):
            self.scrape_senate_vote(bill, vote_link.attrib['href'])

        for vote_link in page.xpath("//a[contains(@href, 'Hrollcal')]"):
            self.scrape_house_vote(bill, vote_link.attrib['href'])

        for doc_link in page.xpath("//a[contains(@href, 'FISCAL')]"):
            num = doc_link.text.strip().split("(")[0]
            bill.add_document("Fiscal Impact Statement #%s" % num,
                              doc_link.attrib['href'])

        bill['subjects'] = self.subjects[bill_id]

        # Also retrieve the "latest printing" bill if it hasn't
        # been found yet.
        latest_printing = '//a[contains(@href, "bills")]/@href'
        for url in set(page.xpath(latest_printing)):

            # Set the mimetype.
            if 'pdf' in url:
                mimetype = 'application/pdf'
            else:
                mimetype = 'text/html'

            try:
                bill.add_version('Latest printing', url,
                                 mimetype=mimetype)
            except ValueError:
                # The url was a duplicate.
                pass

        if not bill['sponsors']:

            # Indiana has so-called 'vehicle bills', which are empty
            # placeholders that may later get injected with content
            # concerning such innocuous topics as redistricting
            # (2011 SB 0192) and marijuana studies (2011 SB 0192).
            url = bill['sources'][0]['url']
            page = self.urlopen(url)
            if 'Vehicle Bill' in page:
                msg = 'Skipping vehicle bill: {bill_id}.'
                self.logger.info(msg.format(**bill))
                return

            # And some bills are withdrawn before first reading, which
            # case they don't really exist, and the main version link
            # will 404.
            withdrawn = 'Withdrawn prior to first reading'
            if bill['actions']:
                if bill['actions'][-1]['action'] == withdrawn:
                    msg = ('Skipping bill withdrawn before first '
                           'reading: {bill_id}.')
                    self.logger.info(msg.format(**bill))
                    return

        self.save_bill(bill)

    def scrape_actions(self, bill, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)

        bill.add_source(url)

        slist = page.xpath("//strong[contains(., 'Authors:')]")[0]
        slist = slist.tail.split(',')
        sponsors = []
        for sponsor in slist:
            name = sponsor.strip()
            if not name:
                continue
            if name == 'Jr.':
                sponsors[-1] = sponsors[-1] + ", Jr."
            else:
                sponsors.append(name)
        for sponsor in sponsors:
            bill.add_sponsor('primary', sponsor)

        act_table = page.xpath("//table")[1]

        for row in act_table.xpath("tr")[1:]:
            date = row.xpath("string(td[1])").strip()
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            # Handle idiot typo of year 1320 instead of 2013.
            if date.year == 1320:
                date = datetime.datetime(
                    year=2013, month=date.month, day=date.day)

            chamber = row.xpath("string(td[2])").strip()
            if chamber == 'S':
                chamber = 'upper'
            elif chamber == 'H':
                chamber = 'lower'

            action = row.xpath("string(td[4])").strip(' ;\t\n')

            if not action:
                # sometimes there are blank actions, just skip these
                continue

            attrs = self.categorizer.categorize(action)

            bill.add_action(chamber, action, date, **attrs)

    def build_subject_mapping(self, session):
        self.subjects = defaultdict(list)

        url = ("http://www.in.gov/apps/lsa/session/billwatch/billinfo"
               "?year=%s&session=1&request=getSubjectList" % session)
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'getSubject')]"):
            subject = link.text.strip()

            self.scrape_subject(subject, link.attrib['href'])

    def scrape_subject(self, subject, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)

        for link in page.xpath("//a[contains(@href, 'getBill')]"):
            self.subjects[link.text.strip()].append(subject)

    def scrape_house_vote(self, bill, url):
        try:
            bill.add_vote(PDFHouseVote(url, self).vote())
        except PDFHouseVote.VoteParseError:
            # It was a scanned, hand-written document, most likely.
            return

    def scrape_senate_vote(self, bill, url):
        (path, resp) = self.urlretrieve(url)
        text = convert_pdf(path, 'text')
        os.remove(path)

        lines = text.split('\n')

        date_match = re.search(r'Date:\s+(\d+/\d+/\d+)', text)
        if not date_match:
            self.log("Couldn't find date on %s" % url)
            return

        time_match = re.search(r'Time:\s+(\d+:\d+:\d+)\s+(AM|PM)', text)
        date = "%s %s %s" % (date_match.group(1), time_match.group(1),
                             time_match.group(2))
        date = datetime.datetime.strptime(date, "%m/%d/%Y %I:%M:%S %p")
        date = self._tz.localize(date)

        vote_type = None
        yes_count, no_count, other_count = None, None, 0
        votes = []
        for line in lines[21:]:
            line = line.strip()
            if not line:
                continue

            if line.startswith('YEAS'):
                yes_count = int(line.split(' - ')[1])
                vote_type = 'yes'
            elif line.startswith('NAYS'):
                no_count = int(line.split(' - ')[1])
                vote_type = 'no'
            elif line.startswith('EXCUSED') or line.startswith('NOT VOTING'):
                other_count += int(line.split(' - ')[1])
                vote_type = 'other'
            else:
                votes.extend([(n.strip(), vote_type)
                              for n in re.split(r'\s{2,}', line)])

        if yes_count is None or no_count is None:
            self.log("Couldne't find vote counts in %s" % url)
            return

        passed = yes_count > no_count + other_count

        clean_bill_id = fix_bill_id(bill['bill_id'])
        motion_line = None
        for i, line in enumerate(lines):
            if line.strip() == clean_bill_id:
                motion_line = i + 2
        motion = lines[motion_line]
        if not motion:
            self.log("Couldn't find motion for %s" % url)
            return

        vote = Vote('upper', date, motion, passed, yes_count, no_count,
                    other_count)
        vote.add_source(url)

        insert_specific_votes(vote, votes)
        check_vote_counts(vote)

        bill.add_vote(vote)
