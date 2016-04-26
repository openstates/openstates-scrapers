import re
import inspect
import datetime
import collections
from itertools import islice

import lxml.html

from billy.scrape.bills import Bill
from billy.scrape.votes import Vote
from billy.utils import term_for_session, metadata
from openstates.utils import LXMLMixin

from .utils import Urls, CachedAttr


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
        self.term_start_year = term_for_session('ny', session)
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

    def _build_sponsors_memo(self):
        url = self.shared_url + '&Memo=Y'
        self.bill.add_document('Sponsor\'s Memorandum', url)
    
    def build_upper_votes(self):
        url = self.senate_url
            
        self.urls.add(votes_upper=url)
        self.bill.add_source(url)
        doc = self.urls.votes_upper.doc
        if doc is None:
            return
            
        actual_vote = collections.defaultdict(list)
        for vote_div in doc.xpath('*//div[@class="c-detail--votes"]/div[contains(@class, "c-bill--vote")]'):
            # make sure its a senate vote
            vote_title, date = [item.strip() for item in vote_div.xpath('*//h3[@class="c-vote-detail--date"]/text()')[0].split(':')]
            date = datetime.datetime.strptime(date, '%b %d, %Y')
            
            yes_count = int(vote_div.xpath('*//div[@class="vote-container"]/div[contains(@class, "aye")]/div[@class="vote-count"]/text()')[0])
            no_count = int(vote_div.xpath('*//div[@class="vote-container"]/div[contains(@class, "nay")]/div[@class="vote-count"]/text()')[0])
            
            passed = yes_count > no_count
            vote = Vote('upper', date, vote_title, passed, yes_count,
                        no_count, other_count=0)
                
            for vote_result_div in vote_div.xpath('*//div[contains(@class, "c-detail--vote-grp")]'):
                result_type = vote_result_div.xpath('div[@class="c-detail--section-title"]/text()')[0].split()[0].strip()
                result_list = vote_result_div.xpath('ul/li/a/text()')
                        
                for name in result_list:
                    name = name.strip()
                    
                    if result_type == 'aye':
                        vote.yes(name)
                    elif result_type == 'nay':
                        vote.no(name)
                    else:
                        vote.other(name)
                        actual_vote[result_type].append(name)
                    
            # The page doesn't provide an other_count.
            vote['other_count'] = len(vote['other_votes'])
            vote['actual_vote'] = actual_vote
            self.bill.add_vote(vote)

    def _build_lower_votes(self):
        url = self.shared_url + '&Votes=Y'
        self.urls.add(votes=url)
        self.bill.add_source(url)
        doc = self.urls.votes.doc
        if doc is None:
            return

        # Grab bill information.
        try:
            pre = doc.xpath('//pre')[0].text_content()

            no_votes = ('There are no votes for this bill in this legislative '
                        'session.')

            if pre == no_votes:
                raise ValueError('No votes for this bill.')
        # Skip bill if votes can't be found.
        except (IndexError, ValueError) as e:
            return

        actual_vote = collections.defaultdict(list)
        for table in doc.xpath('//table'):

            date = table.xpath('caption/label[contains(., "DATE:")]')
            date = date[0].itersiblings().next().text
            date = datetime.datetime.strptime(date, '%m/%d/%Y')

            votes = table.xpath('caption/span/label[contains(., "YEA/NAY:")]')
            votes = votes[0].itersiblings().next().text
            yes_count, no_count = map(int, votes.split('/'))

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
                    key = re.sub(r'^_build_', '', name)
                    member()
