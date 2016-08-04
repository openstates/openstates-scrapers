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

    def _parse_bill_number(self, bill_id):
        bill_id_regex = r'(^[ABCEJKLRS])(\d{,6})'
        bill_id_match = re.search(bill_id_regex, bill_id)
        bill_prefix, bill_number = bill_id_match.groups()

        return (bill_prefix, bill_number)

    def _parse_bill_prefix(self, bill_prefix):
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
            ).format(bill_id=bill_id)

        return (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
                title, (prefix, number, active_version))

    def _parse_senate_votes(self, vote_data):
        vote_datetime = datetime.datetime.strptime(vote_data['voteDate'],
            '%Y-%m-%d')

        vote = Vote(
            chamber='upper',
            date=vote_datetime.date(),
            motion='[No motion available.]',
            passed=False,
            yes_votes=[],
            no_votes=[],
            other_votes=[],
            yes_count=0,
            no_count=0,
            other_count=0)

        if vote_data['voteType'] == 'FLOOR':
            vote['motion'] = 'Floor Vote'
        elif vote_data['voteType'] == 'COMMITTEE':
            vote['motion'] = '{} Vote'.format(vote_data['committee']['name'])
        else:
            raise ValueError('Unknown vote type encountered.')

        vote_rolls = vote_data['memberVotes']['items']

        # Count all yea votes.
        if 'items' in vote_rolls.get('AYE', {}):
            for legislator in vote_rolls['AYE']['items']:
                vote.yes(legislator['fullName'])
                vote['yes_count'] += 1
        if 'items' in vote_rolls.get('AYEWR', {}):
            for legislator in vote_rolls['AYEWR']['items']:
                vote.yes(legislator['fullName'])
                vote['yes_count'] += 1

        # Count all nay votes.
        if 'items' in vote_rolls.get('NAY', {}):
            for legislator in vote_rolls['NAY']['items']:
                vote.no(legislator['fullName'])
                vote['no_count'] += 1

        # Count all other types of votes.
        other_vote_types = ('EXC', 'ABS', 'ABD')
        for vote_type in other_vote_types:
            if vote_rolls.get(vote_type, []):
                for legislator in vote_rolls[vote_type]['items']:
                    vote.other(legislator['fullName'])
                    vote['other_count'] += 1

        vote['passed'] = vote['yes_count'] > vote['no_count']

        return vote

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

        bill = Bill(
            session,
            bill_chamber,
            bill_id,
            title,
            type=bill_type,
            summary=bill_data['summary'])

        if bill_data['title'] is None:
            bill['title'] = bill_data['summary']

        bill_active_version = bill_data['amendments']['items'][active_version]

        # Parse sponsors.
        if bill_data['sponsor']['rules'] == True:
            bill.add_sponsor('primary', 'Rules Committee',
                chamber=bill_chamber)
        elif not bill_data['sponsor']['budget']:
            primary_sponsor = bill_data['sponsor']['member']
            bill.add_sponsor('primary', primary_sponsor['shortName'])

            # There *shouldn't* be cosponsors if there is no sponsor.
            cosponsors = bill_active_version['coSponsors']['items']
            for cosponsor in cosponsors:
                bill.add_sponsor('cosponsor', cosponsor['shortName'])

        # List companion bill.
        same_as = bill_active_version.get('sameAs', {})
        # Check whether "sameAs" property is populated with at least one bill.
        if same_as['items']:
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

        # Parse actions.
        chamber_map = {
            'senate': 'upper',
            'assembly': 'lower',
        }

        for action in bill_data['actions']['items']:
            chamber = chamber_map[action['chamber'].lower()]
            action_datetime = datetime.datetime.strptime(action['date'],
                '%Y-%m-%d')
            action_date = action_datetime.date()
            types, attrs = NYBillScraper.categorizer.categorize(action['text'])

            bill.add_action(
                chamber,
                action['text'],
                action_date,
                type=types,
                **attrs)

        # Chamber-specific processing.
        if bill_chamber == 'upper':
            # Collect votes.
            for vote_data in bill_data['votes']['items']:
                vote = self._parse_senate_votes(vote_data)
                bill.add_vote(vote)
        elif bill_chamber == 'lower':
            assembly = AssemblyBillPage(self, session, bill, details)
            assembly.build()
            assembly_bill_data = assembly.bill

        # A little strange the way it works out, but the Assembly
        # provides the HTML version documents and the Senate provides
        # the PDF version documents.
        amendments = bill_data['amendments']['items']
        for key, amendment in amendments.iteritems():
            version = amendment['printNo']

            html_version = version + ' HTML'
            html_url = 'http://assembly.state.ny.us/leg/?sh=printbill&bn='\
                '{}&term={}'.format(bill_id, self.term_start_year)
            bill.add_version(html_version, html_url, on_duplicate='use_new', mimetype='text/html')

            pdf_version = version + ' PDF'
            pdf_url = 'http://legislation.nysenate.gov/pdf/bills/{}/{}'\
                .format(self.term_start_year, bill_id)
            bill.add_version(pdf_version, pdf_url, on_duplicate='use_new', 
                mimetype='application/pdf')

        # Handling of sources follows. Sources serving either chamber
        # maintain duplicate data, so we can see certain bill data
        # through either chamber's resources. However, we have to refer
        # to a specific chamber's resources if we want to grab certain
        # specific information such as vote data.
        #
        # As such, I'm placing all potential sources in the interest of
        # thoroughness. - Andy Lo

        # List Open Legislation API endpoint as a source.
        bill.add_source(self.api_client.root + self.api_client.\
            resources['bill'].format(
                session_year=session,
                bill_id=bill_id,
                summary='',
                detail=''))
        bill.add_source(senate_url)
        bill.add_source(assembly_url)

        return bill

    def scrape(self, session, chambers):
        self.api_client = OpenLegislationAPIClient(self)

        term_id = term_for_session('ny', session)

        for term in reversed(self.metadata['terms']):
            if term['name'] == term_id:
                self.term_start_year = term['start_year']
                break

        for bill in self._generate_bills(session):
            bill_object = self._scrape_bill(session, bill)
            self.save_bill(bill_object)
