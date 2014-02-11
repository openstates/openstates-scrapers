import os
import re
import datetime
import urlparse
import operator
import itertools
from collections import defaultdict
from contextlib import contextmanager
from StringIO import StringIO

import scrapelib
import requests
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf
from billy.importers.bills import fix_bill_id

import pytz
import lxml.html

from .actions import Categorizer
from .models import parse_vote, BillDocuments, VoteParseError


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

    def scrape(self, term, chambers):
        self.requests_per_minute = 30
        url = 'http://iga.in.gov/legislative/%s/bills/' % term
        self.logger.info('GET ' + url)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        seen_bill_ids = set()

        # First scrape subjects and any bills found on those pages.
        for subject_url, subject in self.generate_subjects():
            subject_bills = self.generate_subject_bills(subject_url)
            for bill_id, bill_url, bill_title in subject_bills:
                chamber = 'upper' if bill_id[0] == 'S' else 'lower'
                self.scrape_bill(
                    chamber, term, bill_id, bill_url, bill_title, subject=subject)
                seen_bill_ids.add(bill_id)

        # Then hit bill index page to catch any uncategorized bills.
        uls = doc.xpath('//ul[contains(@class, "clean-list")]')

        for chamber, ul in zip(chambers, uls):
            for li in ul.xpath('li'):
                bill_id = li.xpath('string(a/strong)')
                if bill_id in seen_bill_ids:
                    continue
                bill_url = li.xpath('string(a/@href)')
                bill_title = li.xpath('a/strong')[0].tail.rstrip().lstrip(': ')
                bill = self.scrape_bill(
                    chamber, term, bill_id, bill_url, bill_title)

    def generate_subjects(self):
        url = 'http://iga.in.gov/legislative/2014/bysubject/'
        self.logger.info('GET ' + url)
        resp = self.get(url)
        html = resp.text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        for li in doc.xpath('//li[contains(@class, "subject-list_item")]'):
            yield li.xpath('string(a/@href)'), li.text_content().strip()

    def generate_subject_bills(self, url):
        self.logger.info('GET ' + url)
        resp = self.get(url)
        html = resp.text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        for row in doc.xpath('//table//tr')[1:]:
            try:
                bill_id = row[2].text_content()
            except IndexError:
                # We hit the last row.
                return
            bill_url = row[2].xpath('string(a/@href)')
            bill_title = row[3].text_content()
            yield bill_id, bill_url, bill_title

    def scrape_bill(self, chamber, term, bill_id, url, title, subject=None):
        self.logger.info('GET ' + url)
        resp = self.get(url)
        html = resp.text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        bill = Bill(term, chamber, bill_id, title)
        bill.add_source(url)
        if subject is not None:
            bill['subjects'] = [subject]

        # Sponsors
        sponsor_map = {
            'author': 'primary',
            'co-author': 'cosponsor',
            'sponsor': 'primary',
            'co-sponsor': 'cosponsor',
            }
        for div in doc.xpath('//div[contains(@class, "bill-author-info")]'):
            name = div.xpath('string(b)').strip()
            sp_type = sponsor_map[div.xpath('string(p)').strip().lower()]
            bill.add_sponsor(sp_type, name)

        # Actions
        for li in doc.xpath('//div[@id="bill-actions"]//li')[::-1]:
            if li.text_content() == 'None currently available.':
                continue
            chamber_str = li.xpath('string(strong)').strip()
            action_chamber = dict(H='lower', S='upper')[chamber_str]
            action_date = li.xpath('string(span[@class="document-date"])')
            action_date = datetime.datetime.strptime(action_date.strip(), '%m/%d/%Y')
            action_text = li.xpath('string(span[2])').strip()
            if not action_text.strip():
                continue
            kwargs = dict(date=action_date, actor=action_chamber, action=action_text)
            kwargs.update(**self.categorizer.categorize(action_text))
            bill.add_action(**kwargs)

        # Documents (including votes)
        for doc_type, doc_meta in BillDocuments(self, doc):
            if doc_type == 'version':
                bill.add_version(
                    doc_meta.title or doc_meta.text, url=doc_meta.url,
                    mimetype='application/pdf')
            elif doc_type == 'document':
                bill.add_document(doc_meta.title or doc_meta.text, url=doc_meta.url,
                    mimetype='application/pdf')
            elif doc_type == 'rollcall':
                self.add_rollcall(chamber, bill, doc_meta)

        self.save_bill(bill)

    def add_rollcall(self, chamber, bill, doc_meta):
        try:
            vote = parse_vote(self, chamber, doc_meta)
            bill.add_vote(vote)
        except VoteParseError:
            # It was a scanned, hand-written document, most likely.
            return

    # def scrape_senate_vote(self, bill, url):
    #     try:
    #         (path, resp) = self.urlretrieve(url)
    #     except:
    #         return
    #     text = convert_pdf(path, 'text')
    #     os.remove(path)

    #     lines = text.split('\n')

    #     date_match = re.search(r'Date:\s+(\d+/\d+/\d+)', text)
    #     if not date_match:
    #         self.log("Couldn't find date on %s" % url)
    #         return

    #     time_match = re.search(r'Time:\s+(\d+:\d+:\d+)\s+(AM|PM)', text)
    #     date = "%s %s %s" % (date_match.group(1), time_match.group(1),
    #                          time_match.group(2))
    #     date = datetime.datetime.strptime(date, "%m/%d/%Y %I:%M:%S %p")
    #     date = self._tz.localize(date)

    #     vote_type = None
    #     yes_count, no_count, other_count = None, None, 0
    #     votes = []
    #     for line in lines[21:]:
    #         line = line.strip()
    #         if not line:
    #             continue

    #         if line.startswith('YEAS'):
    #             yes_count = int(line.split(' - ')[1])
    #             vote_type = 'yes'
    #         elif line.startswith('NAYS'):
    #             no_count = int(line.split(' - ')[1])
    #             vote_type = 'no'
    #         elif line.startswith('EXCUSED') or line.startswith('NOT VOTING'):
    #             other_count += int(line.split(' - ')[1])
    #             vote_type = 'other'
    #         else:
    #             votes.extend([(n.strip(), vote_type)
    #                           for n in re.split(r'\s{2,}', line)])

    #     if yes_count is None or no_count is None:
    #         self.log("Couldne't find vote counts in %s" % url)
    #         return

    #     passed = yes_count > no_count + other_count

    #     clean_bill_id = fix_bill_id(bill['bill_id'])
    #     motion_line = None
    #     for i, line in enumerate(lines):
    #         if line.strip() == clean_bill_id:
    #             motion_line = i + 2
    #     motion = lines[motion_line]
    #     if not motion:
    #         self.log("Couldn't find motion for %s" % url)
    #         return

    #     vote = Vote('upper', date, motion, passed, yes_count, no_count,
    #                 other_count)
    #     vote.add_source(url)

    #     insert_specific_votes(vote, votes)
    #     check_vote_counts(vote)

    #     bill.add_vote(vote)

