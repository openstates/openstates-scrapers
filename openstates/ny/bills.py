import re
import datetime
import scrapelib
import lxml.html
import lxml.etree
from collections import defaultdict
from billy.utils import term_for_session
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from apiclient import OpenLegislationAPIClient
from .models import AssemblyBillPage
from .actions import Categorizer


class NYBillScraper(BillScraper):
    jurisdiction = 'ny'
    categorizer = Categorizer()

    def _date_from_timestamp(self, timestamp):
        return datetime.datetime.fromtimestamp(int(timestamp) / 1000)

    def _parse_bill_number(self, bill_id):
        bill_id_regex = r'(^[ABCEJKLRS])(\d{,6})'
        bill_id_match = re.search(bill_id_regex, bill_id)
        bill_prefix, bill_number = bill_id_match.groups()

        return (bill_prefix, bill_number)

    def _parse_bill_prefix(self, bill_prefix):
        """
        Legacy holdover, but still useful for determining companion bill
        chambers.
        """
        bill_chamber, bill_type = {
            'S': ('upper', 'bill'),
            'R': ('upper', 'resolution'),
            'J': ('upper', 'legislative resolution'),
            'B': ('upper', 'concurrent resolution'),
            'C': ('lower', 'concurrent resolution'),
            'A': ('lower', 'bill'),
            'E': ('lower', 'resolution'),
            'K': ('lower', 'legislative resolution'),
            'L': ('lower', 'joint resolution')}[bill_prefix]

        return (bill_chamber, bill_type)

    def _parse_bill_details(self, bill):
        bill_id = bill['printNo']
        assert bill_id

        # Parse the bill ID into its prefix and number.
        prefix, number = self._parse_bill_number(bill_id)

        bill_type = self._parse_bill_prefix(prefix)[1]

        active_version = bill['activeVersion']

        title = bill['title'].strip()

        if not title:
            self.logger.warn('Bill missing title.')
            return
        
        # Determine the chamber the bill originated from.
        if bill['billType']['chamber'] == 'SENATE':
            bill_chamber = 'upper'
        elif bill['billType']['chamber'] == 'ASSEMBLY':
            bill_chamber = 'lower'
        else:
            warning = 'Could not identify chamber for {}.'
            self.logger.warn(warning).format(bill_id)

        senate_url = (
            'http://www.nysenate.gov/legislation/bills/{bill_session}/'
            '{bill_id}'
        ).format(
            bill_session=bill['session'], bill_id=bill_id)

        assembly_url = (
            'http://assembly.state.ny.us/leg/?default_fld=&bn={bill_id}'
            '&Summary=Y&Actions=Y'
        ).format(
            bill_id=bill_id)

        return (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
                title, (prefix, number, active_version))

    def _generate_bills(self, session):
        self.logger.info('Generating bills.')
        bills = defaultdict(list)

        delimiter = '-'
        (start_year, delimiter, end_year) = session.partition(delimiter)
        page = 0
        # 1000 is the current maximum returned record limit for all Open
        # Legislature API calls that use the parameter.
        limit = 1000
        # Flag whether to retrieve full bill data.
        full = True
        while True:
            # Updating the offset before the page matters here.
            offset = limit * page + 1
            page += 1

            # Response should be a dict of the JSON data returned from
            # the Open Legislation API.
            response = self.api_client.get('bills', session_year=start_year,
                limit=limit, offset=offset, full=full)

            if response['responseType'] == 'empty list'\
                or response['offsetStart'] > response['offsetEnd']:
                break
            else:
                bills = response['result']['items']

            for bill in bills:
                yield bill

    def _scrape_bill(self, session, bill_data):
        details = self._parse_bill_details(bill_data)

        (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
         title, (prefix, number, active_version)) = details

        """
        Note: This needs to scrape both assembly and senate sites.
        Neither house has the other's votes, so you have to scrape both
        and merge them.
        """
        assembly = AssemblyBillPage(self, session, bill_chamber, details)
        assembly.build()
        bill = assembly.bill
        bill.add_source(assembly_url)

        # Add companion bill.
        same_as = bill_data.get('amendments', {}).get('items', {})\
            .get(active_version, {}).get('sameAs', {})
        # Check whether "sameAs" property is populated with at least one bill.
        if same_as and 'items' in same_as and 'size' in same_as and\
            same_as['size'] > 0:
            # Get companion bill ID.
            companion_bill_id = same_as['items'][0]['basePrintNo']

            # Build companion bill session.
            start_year = same_as['items'][0]['session']
            end_year = start_year + 1
            companion_bill_session = '-'.join([str(start_year), str(end_year)])

            # Determine companion bill chamber.
            companion_bill_prefix = self._parse_bill_number(
                same_as['items'][0]['basePrintNo'])[0]
            companion_bill_chamber = self._parse_bill_prefix(
                companion_bill_prefix)[0]

            # Attach companion bill data.
            bill.add_companion(
                companion_bill_id,
                companion_bill_session,
                companion_bill_chamber,
            )

        # Determine whether to count votes.
        votes_detected = False
        try:
            # This counts the vote categories, not the votes themselves
            # (i.e. AYE, NAY, EXC).  If a category is present, there
            # should be votes available to record.
            if bill_data['votes']['memberVotes']['size'] > 0:
                votes_detected = True
        except KeyError:
            pass

        if votes_detected:
            for vote_data in bill_data['votes']['memberVotes']:
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

                # Count all yea votes.
                if 'items' in vote_data.get('AYE', {}):
                    for legislator in vote_data['AYE']['items']:
                        vote.yes(legislator['fullName'])
                        vote['yes_count'] += 1
                if 'items' in vote_data.get('AYEWR', {}):
                    for legislator in vote_data['AYEWR']['items']:
                        vote.yes(legislator['fullName'])
                        vote['yes_count'] += 1

                # Count all nay votes.
                if 'items' in vote_data.get('NAY', {}):
                    for legislator in vote_data['NAY']['items']:
                        vote.no(legislator['fullName'])
                        vote['no_count'] += 1

                # Count all non-yea/nay votes.
                other_vote_types = ('EXC', 'ABS', 'ABD')
                for vote_type in other_vote_types:
                    if 'items' in vote_data.get(vote_type, {}):
                        for legislator in vote_data[vote_type]['items']:
                            vote.other(legislator['fullName'])
                            vote['other_count'] += 1

                vote['passed'] = vote['yes_count'] > vote['no_count']

                bill.add_vote(vote)

        if bill_data['title'] is None:
            bill['title'] = bill_data['summary']

        return bill

    def scrape(self, session, chambers):
        self.api_client = OpenLegislationAPIClient(self)

        term_id = term_for_session('ny', session)

        for term in self.metadata['terms']:
            if term['name'] == term_id:
                break

        self.term = term

        for bill in self._generate_bills(session):
            bill_object = self._scrape_bill(session, bill)
            self.save_bill(bill_object)
