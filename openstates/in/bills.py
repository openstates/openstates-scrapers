import re
import datetime

import scrapelib
from billy.scrape.bills import BillScraper, Bill

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
        if 0 < self._requests_per_minute:
            self.requests_per_minute = 30
        seen_bill_ids = set()

        # Get resolutions.
        url = 'http://iga.in.gov/legislative/{}/resolutions'.format(term)
        self.logger.info('GET ' + url)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        for a in doc.xpath('//strong/ancestor::a'):
            bill_id = a.text_content().strip()
            bill_chamber = ('upper' if bill_id[0] in 'SJ' else 'lower')
            bill_url = a.attrib['href']
            bill_title = a.xpath('string(./following-sibling::em)').strip()
            self.scrape_bill(bill_chamber, term, bill_id, bill_url, bill_title)

        url = 'http://iga.in.gov/legislative/%s/bills/' % term
        self.logger.info('GET ' + url)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)


        # First scrape subjects and any bills found on those pages.
        for subject_url, subject in self.generate_subjects(term):
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
                try:
                    bill_title = li.xpath('a/strong')[0].tail.rstrip().lstrip(': ')
                except IndexError:
                    continue
                self.scrape_bill(chamber, term, bill_id, bill_url, bill_title)

    def generate_subjects(self, term):
        url = 'http://iga.in.gov/legislative/{}/bysubject/'.format(term)
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

    bill_types = {
        'HB': 'bill',
        'HC': None,
        'HCR': 'concurrent resolution',
        'HJ': None,
        'HJR': 'joint resolution',
        'HR': 'resolution',
        'SB': 'bill',
        'SC': None,
        'SCR': 'concurrent resolution',
        'SJ': None,
        'SJR': 'joint resolution',
        'SR': 'resolution'
        }

    def get_bill_type(self, bill_id):
        letters = re.search(r'^\s*([A-Za-z]+)', bill_id).group(1)
        return self.bill_types.get(letters)

    def scrape_bill(self, chamber, term, bill_id, url, title, subject=None):
        self.logger.info('GET ' + url)
        try:
            resp = self.get(url)
        except scrapelib.HTTPError:
            return

        html = resp.text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        type_ = self.get_bill_type(bill_id)
        if type_ is None:
            # Skip if the bill isn't a bill or resolution. IN has lots of
            # bad data.
            return

        bill = Bill(term, chamber, bill_id, title, type=type_)
        bill.add_source(url)
        if subject is not None:
            bill['subjects'] = [subject]

        # Sponsors
        sponsor_map = {
            'author': 'primary',
            'co-author': 'cosponsor',
            'sponsor': 'cosponsor',
            'co-sponsor': 'cosponsor',
            }
        for div in doc.xpath('//div[contains(@class, "bill-author-info")]'):
            name = div.xpath('string(em)').strip()
            sp_type = sponsor_map[div.xpath('string(p)').strip().lower()]
            bill.add_sponsor(sp_type, name)

        # Actions
        for li in doc.xpath('//table[contains(@class,"actions-table")]//dd')[::-1]:
            if li.text_content() == 'None currently available.':
                continue
            chamber_str, action_date = li.xpath('./b/span/text()')
            chambers = dict(H='lower', S='upper', G='executive')
            if chamber_str not in chambers:
                action_chamber = chamber
            else:
                action_chamber = chambers[chamber_str]


            # Some resolution actions have no dates.
            if not action_date.strip():
                continue
            action_date = datetime.datetime.strptime(action_date.strip(), '%m/%d/%Y')
            action_text = li.xpath('./text()')[1].strip()

            if not action_text.strip():
                continue
            if not "referred to the house" in action_text.lower() and "referred to the senate" not in action_text.lower():
                #removing bills being referred to house/senate because they were being treated like committees
                #should prob be fixed in the regexes in actions.py someday
                kwargs = dict(date=action_date, actor=action_chamber, action=action_text)
                kwargs.update(**self.categorizer.categorize(action_text))
                bill.add_action(**kwargs)

        # Documents (including votes)
        print doc.xpath("./@href")
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
