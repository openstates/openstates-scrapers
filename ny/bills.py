'''Note, this needs to scrape both assembly and senate sites. Neither
house has the other's votes, so you have to scrape both and merge them.
'''
import re
import datetime
from collections import defaultdict

from billy.utils import term_for_session
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import scrapelib
import lxml.html
import lxml.etree

from .models import AssemblyBillPage, SenateBillPage
from .actions import Categorizer


class NYBillScraper(BillScraper):

    jurisdiction = 'ny'
    categorizer = Categorizer()

    def scrape(self, session, chambers):
        term_id = term_for_session('ny', session)
        for term in self.metadata['terms']:
            if term['name'] == term_id:
                break
        self.term = term
        for billset in self.yield_grouped_versions():
            self.scrape_bill(session, billset)

    def scrape_bill(self, session, bills):

        billdata, details = bills[0]

        (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
         title, (letter, number, is_amd)) = details

        data = billdata['data']['bill']

        assembly = AssemblyBillPage(self, session, bill_chamber, details)
        assembly.build()
        bill = assembly.bill
        bill.add_source(billdata['url'])

        # Add companion.
        if data['sameAs']:
            bill.add_companion(data['sameAs'])

        if data['summary']:
            bill['summary'] = data['summary']

        if data['votes']:
            for vote_data in data['votes']:
                vote = Vote(
                    chamber='upper',
                    date=self.date_from_timestamp(vote_data['voteDate']),
                    motion=vote_data['description'] or '[No motion available.]',
                    passed=False,
                    yes_votes=[],
                    no_votes=[],
                    other_votes=[],
                    yes_count=0,
                    no_count=0,
                    other_count=0)

                for name in vote_data['ayes']:
                    vote.yes(name)
                    vote['yes_count'] += 1
                for names in map(vote_data.get, ['absent', 'excused', 'abstains']):
                    for name in names:
                        vote.other(name)
                        vote['other_count'] += 1
                for name in vote_data['nays']:
                    vote.no(name)
                    vote['no_count'] += 1

                vote['passed'] = vote['yes_count'] > vote['no_count']

                bill.add_vote(vote)

        # if data['previousVersions']:
        #   These are instances of the same bill from prior sessions.
        #     import pdb; pdb.set_trace()

        if not data['title']:
            bill['title'] = bill['summary']

        self.save_bill(bill)

    def date_from_timestamp(self, timestamp):
        return datetime.datetime.fromtimestamp(int(timestamp) / 1000)

    def bill_id_details(self, billdata):
        data = billdata['data']['bill']
        api_id = billdata['oid']
        source_url = billdata['url']

        title = data['title'].strip()
        if not title:
            return

        # Parse the bill_id into beginning letter, number
        # and any trailing letters indicating its an amendment.
        bill_id, year = api_id.split('-')
        bill_id_rgx = r'(^[A-Z])(\d{,6})([A-Z]{,3})'
        bill_id_base = re.search(bill_id_rgx, bill_id)
        letter, number, is_amd = bill_id_base.groups()

        bill_chamber, bill_type = {
            'S': ('upper', 'bill'),
            'R': ('upper', 'resolution'),
            'J': ('upper', 'legislative resolution'),
            'B': ('upper', 'concurrent resolution'),
            'C': ('lower', 'concurrent resolution'),
            'A': ('lower', 'bill'),
            'E': ('lower', 'resolution'),
            'K': ('lower', 'legislative resolution'),
            'L': ('lower', 'joint resolution')}[letter]

        senate_url = billdata['url']

        assembly_url = (
            'http://assembly.state.ny.us/leg/?'
            'default_fld=&bn=%s&Summary=Y&Actions=Y') % bill_id

        return (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
                title, (letter, number, is_amd))


    def yield_api_bills(self):
        '''Yield individual versions. The caller can get all versions
        for a particular ID, process the group, then throw everything
        away and move onto the next ID.
        '''
        # The bill api object keys we'll actually use. Throw rest away.
        keys = set([
            'coSponsors', 'multiSponsors', 'sponsor', 'actions',
            'versions', 'votes', 'title', 'sameAs', 'summary'])

        index = 0
        bills = defaultdict(list)

        billdata = defaultdict(lambda: defaultdict(list))
        for year in (self.term['start_year'], self.term['end_year']):
            while True:
                index += 1
                url = (
                    'http://open.nysenate.gov/legislation/2.0/search.json'
                    '?term=otype:bill AND year:2015&pageSize=20&pageIdx=%d'
                    )
                url = url % index
                self.logger.info('GET ' + url)
                resp = self.get(url)

                data = resp.json()
                if not data['response']['results']:
                    break

                for bill in data['response']['results']:
                    billdata = bill['data']['bill']
                    for junk in set(billdata) - keys:
                        del billdata[junk]

                    details = self.bill_id_details(bill)
                    if details is None:
                        continue
                    (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
                     title, (letter, number, is_amd)) = details

                    key = (letter, number)
                    yield key, bill, details

    def yield_grouped_versions(self):
        '''Generates a lists of versions grouped by bill id.
        '''
        prev_key = None
        versions = []
        for key, bill, details in self.yield_api_bills():
            if key is not prev_key and versions:
                yield versions
                versions = []
            versions.append((bill, details))
            prev_key = key


