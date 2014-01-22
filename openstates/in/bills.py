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
            data = self.client.get_relurl(data['link'])
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

        for cosponsponsor in data['cosponsors']:
            name = '%s %s' % (cosponsor['firstName'], cosponsor['lastName'])
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

        self.save_bill(bill)

