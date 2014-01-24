import os
import re
import datetime
import urlparse
from collections import defaultdict
from contextlib import contextmanager

import scrapelib
import requests
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf
from billy.importers.bills import fix_bill_id

import pytz
import lxml.html

from .apiclient import ApiClient, BadApiResponse
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

    # Can turn this on or off. There are thousands of subjects and it takes hours.
    SCRAPE_SUBJECTS = True

    def scrape(self, chamber, session):

        # self.retry_attempts = 0
        self.session = session
        self.chamber = chamber

        self.client = ApiClient(self)
        self.api_session = int(session)
        self.api_chamber = dict(upper='senate', lower='house')[chamber]

        if self.SCRAPE_SUBJECTS:
            self.get_subjects()

        bills = self.client.get('chamber_bills',
            session=self.api_session, chamber=self.api_chamber)
        bills = self.client.unpaginate(bills)
        for data in bills:
            try:
                data = self.client.get_relurl(data['link'])
            except BadApiResponse:
                self.logger.warning('Skipping due to 500 error: %r' % data)
                continue
            except requests.exceptions.ConnectionError:
                self.logger.warning('Skipping due to connection error: %r' % data)
                continue

            try:
                self.scrape_bill(data)
            except BadApiResponse as exc:
                msg = 'Skipping bill due to bad API response at %r: %s'
                self.warning(msg % (exc.resp, exc.resp.text))
                continue

    def get_subjects(self):
        bill2subjects = defaultdict(list)
        subjects = self.client.get('subjects', session=self.api_session)
        subjects = self.client.unpaginate(subjects)
        for subject in subjects:
            if subject['link'] == '/2013/subjects/si_workers_compensation_7426':
                self.warning('Skipping known messed up subject')
                continue
            bills = self.client.get_relurl(subject['link'])
            for bill in bills['bills']:
                bill2subjects[bill['billName']].append(subject['entry'])
        self.bill2subjects = bill2subjects

    @contextmanager
    def skip_api_errors(self, msg):
        try:
            yield
        except BadApiResponse as exc:
            self.warning(msg.format(resp=exc.resp))
        except requests.exceptions.ConnectionError:
            self.warning('Got a connection error. Skipping.')

    def scrape_bill(self, data):
        bill = Bill(
            self.session, self.chamber,
            data['billName'],
            data['title'] or data['latestVersion']['title'] or data['latestVersion']['digest'],
            type=data['type'].lower())

        url = urlparse.urljoin(self.client.root, data['link'])
        bill.add_source(url)

        for author in data['authors'] + data['coauthors']:
            name = '%s %s' % (author['firstName'], author['lastName'])
            bill.add_sponsor('primary', name)

        for spons in data['cosponsors']:
            name = '%s %s' % (spons['firstName'], spons['lastName'])
            bill.add_sponsor('cosponsor', name)

        version_urls = set()
        for version in data['versions']:
            url = urlparse.urljoin(self.client.root, version['link'])
            if url in version_urls:
                continue
            version_urls.add(url)

            msg = 'Skipping version api error {resp.status_code}: {resp.text}'
            with self.skip_api_errors(msg):
                version = self.client.get_relurl(url)
                name = version['printVersionName']
                bill['summary'] = version['digest']
                version_url = urlparse.urljoin(
                    self.client.root, version['pdfDownloadLink'])
                bill.add_version(name, version_url, mimetype='application/pdf')

        actions = self.client.get_relurl(data['actions']['link'])
        action_chambers = dict(House='lower', Senate='upper')
        for action in self.client.unpaginate(actions):
            try:
                date = datetime.datetime.strptime(action['date'], '%Y-%m-%dT%H:%M:%S')
            except TypeError:
                self.warning('Skipping action due to null date: %r' % action)
                continue
            text = action['description']

            # Some are inexplicably blank.
            if not text.strip():
                continue

            action_chamber = action_chambers[action['chamber']['name']]
            kwargs = dict(date=date, actor=self.chamber, action=text)
            kwargs.update(**self.categorizer.categorize(text))
            bill.add_action(**kwargs)

        if self.SCRAPE_SUBJECTS:
            bill['subjects'] = self.bill2subjects[data['billName']]

        msg = 'Skipped rollcall response: {resp.status_code}: {resp.text}'
        with self.skip_api_errors(msg):
            rollcalls = self.client.get('bill_rollcalls',
                session=self.api_session, bill_id=data['billName'])
            # Todo: get the rollcalls.
            import pdb; pdb.set_trace()

        self.save_bill(bill)

    def scrape_house_vote(self, bill, url):
        try:
            bill.add_vote(PDFHouseVote(url, self).vote())
        except PDFHouseVote.VoteParseError:
            # It was a scanned, hand-written document, most likely.
            return

    def scrape_senate_vote(self, bill, url):
        try:
            (path, resp) = self.urlretrieve(url)
        except:
            return
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
