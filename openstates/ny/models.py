import re
import inspect

from openstates.utils import LXMLMixin
from pupa.scrape import VoteEvent

from .utils import Urls
import datetime
from pytz import timezone


class AssemblyBillPage(LXMLMixin):
    '''
    Adapted from an very weirdly overengineered solution that existed
    in this file beforehand. Retained in the interest of time, but the
    remnants of this solution needs to be factored out.

    Takes a bill and edits it in-place with the memo, summary, assembly
    floor votes from the assembly page.
    '''

    def __init__(self, scraper, session, bill, details):
        (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
            title, bill_id_parts) = details

        self.bill = bill
        self.bill_id = bill_id
        # This works on the assumption that the metadata term ID is
        # only the start year.
        self.term_start_year = session.split('-')[0]

        self.letter, self.number, self.version = bill_id_parts
        self.shared_url = 'http://assembly.state.ny.us/leg/?default_fld='\
            '&bn={}&term={}'.format(self.bill_id, self.term_start_year)
        self.urls = Urls(scraper=scraper, urls={
            'assembly': assembly_url,
            'senate': senate_url})

    def _scrub_name(self, name):
        junk = [
            r'^Rules\s+',
            '\(2nd Vice Chairperson\)',
            '\(MS\)',
            'Assemblyman',
            'Assemblywoman',
            'Senator']
        for rgx in junk:
            name = re.sub(rgx, '', name, re.I)

        # Collapse whitespace.
        name = re.sub('\s+', ' ', name)
        return name.strip('(), ')

    def build(self):
        '''Run all the build_* functions.
        '''
        for name, member in inspect.getmembers(self):
            if inspect.ismethod(member):
                if name.startswith('_build_'):
                    yield member()

    def _build_lower_votes(self):
        url = self.shared_url + '&Floor%26nbspVotes=Y'
        self.urls.add(votes=url)
        self.bill.add_source(url)
        doc = self.urls.votes.doc
        if doc is None:
            return

        # Grab bill information.
        try:
            pre = doc.xpath('//pre')[0].text_content().strip()

            no_votes = 'There are no votes for this bill in this legislative '

            if pre == no_votes:
                raise ValueError('No votes for this bill.')
        # Skip bill if votes can't be found.
        except (IndexError, ValueError) as e:
            return

        for table in doc.xpath('//table'):

            date = table.xpath('caption/span[contains(., "DATE:")]')
            date = next(date[0].itersiblings()).text
            date = datetime.datetime.strptime(date, '%m/%d/%Y')
            date = date.replace(tzinfo=timezone('UTC'))

            votes = table.xpath('caption/span/span')[0].text.split(':')[1].split('/')
            yes_count, no_count = map(int, votes)
            passed = yes_count > no_count
            vote = VoteEvent(
                chamber='lower',
                start_date=date,
                motion_text='Floor Vote',
                bill=self.bill,
                result='pass' if passed else 'fail',
                classification='passage'
            )

            vote.set_count('yes', yes_count)
            vote.set_count('no', no_count)
            absent_count = 0
            excused_count = 0
            tds = table.xpath('tr/td/text()')
            votes = [tds[i:i+2] for i in range(0, len(tds), 2)]

            vote_dictionary = {
                'Y': 'yes',
                'NO': 'no',
                'ER': 'excused',
                'AB': 'absent',
                'NV': 'not voting'
            }

            for vote_pair in votes:
                name, vote_val = vote_pair
                vote.vote(vote_dictionary[vote_val], name)
                if vote_val == 'AB':
                    absent_count += 1
                elif vote_val == 'ER':
                    excused_count += 1

            vote.set_count('absent', absent_count)
            vote.set_count('excused', excused_count)
            vote.add_source(url)
            yield vote
