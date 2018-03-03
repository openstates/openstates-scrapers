import collections
import datetime
import re
import inspect

from itertools import islice

from billy.scrape.votes import Vote
from openstates.utils import LXMLMixin
from .utils import Urls


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
        junk = (re.compile(rgx) for rgx in [
            r'^Rules\s+',
            '\(2nd Vice Chairperson\)',
            '\(MS\)',
            'Assemblyman',
            'Assemblywoman',
            'Senator'])
        for rgx in junk:
            name = rgx.sub('', name, re.I)

        # Collapse whitespace.
        name = re.sub('\s+', ' ', name)
        return name.strip('(), ')

    def _build_sponsors_memo(self):
        url = self.shared_url + '&Memo=Y'
        self.bill.add_document('Sponsor\'s Memorandum', url)

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
            'session.'

            if pre == no_votes:
                raise ValueError('No votes for this bill.')
        # Skip bill if votes can't be found.
        except (IndexError, ValueError) as e:
            return

        actual_vote = collections.defaultdict(list)
        for table in doc.xpath('//table'):

            date = table.xpath('caption/span[contains(., "DATE:")]')
            date = next(date[0].itersiblings()).text
            date = datetime.datetime.strptime(date, '%m/%d/%Y')

            votes = table.xpath('caption/span/span')[0].text.split(':')[1].split('/')
            yes_count, no_count = map(int, votes)

            passed = yes_count > no_count
            vote = Vote('lower', date, 'Floor Vote', passed, yes_count,
                        no_count, other_count=0)

            tds = table.xpath('tr/td/text()')
            votes = iter(tds)
            while True:
                try:
                    data = list(islice(votes, 2))
                    name, vote_val = data
                except (StopIteration, ValueError):
                    # End of data. Stop.
                    break
                name = self._scrub_name(name)

                if vote_val.strip() == 'Y':
                    vote.yes(name)
                elif vote_val.strip() in ('N', 'NO'):
                    vote.no(name)
                else:
                    vote.other(name)
                    actual_vote[vote_val].append(name)

            # The page doesn't provide an other_count.
            vote['other_count'] = len(vote['other_votes'])
            vote['actual_vote'] = actual_vote
            self.bill.add_vote(vote)

    def build(self):
        '''Run all the build_* functions.
        '''
        for name, member in inspect.getmembers(self):
            if inspect.ismethod(member):
                if name.startswith('_build_'):
                    member()
