'''OVERENGINEERING FTW!
'''
import re
import inspect
import datetime
import collections
from itertools import islice

import lxml.html

from billy.scrape.bills import Bill
from billy.scrape.votes import Vote
from billy.utils import term_for_session, metadata

from .utils import Urls, CachedAttr


class BasePageyThing(object):
    metadata = metadata('ny')
    chamber_name = None
    def __init__(self, scraper, session, chamber, details):
        (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
          title, bill_id_parts) = details

        self.scraper = scraper
        self.session = session
        self.chamber = chamber
        self.data = {}
        self.bill = Bill(session, bill_chamber, bill_id, title, type=bill_type)

        self.term = term_for_session('ny', session)
        for data in self.metadata['terms']:
            if session in data['sessions']:
                self.termdata = data
            self.term_start_year = data['start_year']

        self.assembly_url = assembly_url
        self.senate_url = senate_url
        self.bill_chamber = bill_chamber
        self.bill_type = bill_type
        self.bill_id = bill_id
        self.title = title
        self.letter, self.number, self.version = bill_id_parts

        self.urls = Urls(scraper=self.scraper, urls={
            'assembly': assembly_url,
            'senate': senate_url})

    def build(self):
        '''Run all the build_* functions.
        '''
        for name, member in inspect.getmembers(self):
            if inspect.ismethod(member):
                if name.startswith('build_'):
                    key = re.sub(r'^build_', '', name)
                    member()


class AssemblyBillPage(BasePageyThing):
    '''Get the actions, sponsors, sponsors memo and summary
    and assembly floor votes from the assembly page.
    '''
    @CachedAttr
    def chunks(self):
        url = ('http://assembly.state.ny.us/leg/?default_fld=&'
               'bn=%s&Summary=Y&Actions=Y&term=%s')
        url = url % (self.bill_id, self.term_start_year)
        self.urls.add(summary=url)
        self.bill.add_source(url)
        summary, actions = self.urls.summary.xpath('//pre')[:2]
        summary = summary.text_content()
        actions = actions.text_content()
        self.data['summary'] = summary
        self.data['actions'] = actions
        return summary, actions

    def build_version(self):
        url = 'http://assembly.state.ny.us/leg/?sh=printbill&bn=%s&term=%s'
        url = url % (self.bill_id, self.term_start_year)
        version = self.bill_id
        self.bill.add_version(version, url, mimetype='text/html')

    def build_companions(self):
        summary, _ = self.chunks
        chunks = summary.split('\n\n')
        for chunk in chunks:
            if chunk.startswith('SAME AS'):
                companions = chunk.replace('SAME AS    ', '').strip()
                if companions != 'No same as':
                    for companion in re.split(r'\s*[\,\\]\s*', companions):
                        companion = re.sub(r'^(?i)Same as ', '', companion)
                        companion = re.sub(r'^Uni', '', companion)
                        companion = re.sub(r'\-\w+$', '', companion)
                        self.bill.add_companion(companion)

    def build_sponsors_memo(self):
        if self.chamber == 'lower':
            url = ('http://assembly.state.ny.us/leg/?'
                   'default_fld=&bn=%s&term=%s&Memo=Y')
            url = url % (self.bill_id, self.term_start_year)
            self.bill.add_document("Sponsor's Memorandum", url)

    def build_summary(self):
        summary, _ = self.chunks
        chunks = summary.split('\n\n')
        self.bill['summary'] = ' '.join(chunks[-1].split())

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

        # Collabpse whitespace.
        name = re.sub('\s+', ' ', name)
        return name.strip('(), ')

    def build_sponsors(self):
        summary, _ = self.chunks
        chunks = summary.split('\n\n')
        for chunk in chunks:
            for sponsor_type in ('SPONSOR', 'COSPNSR', 'MLTSPNSR'):
                if chunk.startswith(sponsor_type):
                    _, data = chunk.split(' ', 1)
                    for sponsor in re.split(r',\s+', data.strip()):

                        if not sponsor:
                            continue

                        # If it's a "Rules" bill, add the Rules committee
                        # as the primary.
                        if sponsor.startswith('Rules'):
                            self.bill.add_sponsor('primary', 'Rules Committee',
                                                  chamber='lower')

                        sponsor = self._scrub_name(sponsor)

                        # Figure out sponsor type.
                        spons_swap = {'SPONSOR': 'primary'}
                        _sponsor_type = spons_swap.get(
                            sponsor_type, 'cosponsor')

                        self.bill.add_sponsor(_sponsor_type, sponsor.strip(),
                                         official_type=sponsor_type)

    def build_actions(self):
        _, actions = self.chunks
        categorizer = self.scraper.categorizer
        actions_rgx = r'(\d{2}/\d{2}/\d{4})\s+(.+)'
        actions_data = re.findall(actions_rgx, actions)
        for date, action in actions_data:
            date = datetime.datetime.strptime(date, r'%m/%d/%Y')
            act_chamber = ('upper' if action.isupper() else 'lower')
            types, attrs = categorizer.categorize(action)
            self.bill.add_action(act_chamber, action, date, type=types, **attrs)
            # Bail if the bill has been substituted by another.
            if 'substituted by' in action:
                return

    def build_lower_votes(self):

        url = ('http://assembly.state.ny.us/leg/?'
               'default_fld=&bn=%s&term=%s&Votes=Y')
        url = url % (self.bill_id, self.term_start_year)
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


class SenateBillPage(object):
    '''Used for categories, senate votes, events.'''

    def __init__(self, scraper, session, chamber, bill, details):
        (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
          title, (letter, number, is_amd)) = details

    def build_subjects(self):
        subjects = []
        for link in self.doc.xpath("//a[contains(@href, 'lawsection')]"):
            subjects.append(link.text.strip())

        self.bill['subjects'] = subjects

    def build_sponsors_memo(self):
        if self.chamber == 'upper':
            self.bill.add_document("Sponsor's Memorandum", self.url)

    def build_senate_votes(self):
        xpath = "//div/b[starts-with(., 'VOTE: FLOOR VOTE:')]"
        for b in self.urls.senate.xpath(xpath):
            date = b.text.split('-')[1].strip()
            date = datetime.datetime.strptime(date, "%b %d, %Y").date()

            yes_votes, no_votes, other_votes = [], [], []
            yes_count, no_count, other_count = 0, 0, 0
            actual_vote = collections.defaultdict(list)

            vtype = None
            for tag in b.xpath("following-sibling::blockquote/*"):
                if tag.tag == 'b':
                    text = tag.text
                    if text.startswith('Ayes'):
                        vtype = 'yes'
                        yes_count = int(re.search(
                            r'\((\d+)\):', text).group(1))
                    elif text.startswith('Nays'):
                        vtype = 'no'
                        no_count = int(re.search(
                            r'\((\d+)\):', text).group(1))
                    elif (text.startswith('Excused') or
                          text.startswith('Abstain') or
                          text.startswith('Absent')
                         ):
                        vtype = 'other'
                        other_count += int(re.search(
                            r'\((\d+)\):', text).group(1))
                    else:
                        raise ValueError('bad vote type: %s' % tag.text)
                elif tag.tag == 'a':
                    name = tag.text.strip()
                    if vtype == 'yes':
                        yes_votes.append(name)
                    elif vtype == 'no':
                        no_votes.append(name)
                    elif vtype == 'other':
                        other_votes.append((name, tag.text))

            passed = yes_count > (no_count + other_count)

            vote = Vote('upper', date, 'Floor Vote', passed, yes_count,
                        no_count, other_count)

            for name in yes_votes:
                vote.yes(name)
            for name in no_votes:
                vote.no(name)
            for name, vote_val in other_votes:
                vote.other(name)
                actual_vote[vote_val].append(name)

            vote['actual_vote'] = actual_vote
            vote.add_source(self.url)
            self.bill.add_vote(vote)

        xpath = "//div/b[starts-with(., 'VOTE: COMMITTEE VOTE:')]"
        for b in self.urls.senate.xpath(xpath):
            _, committee, date = re.split(r'\s*\t+\s*-\s*', b.text)
            date = date.strip()
            date = datetime.datetime.strptime(date, "%b %d, %Y").date()

            yes_votes, no_votes, other_votes = [], [], []
            yes_count, no_count, other_count = 0, 0, 0

            vtype = None
            for tag in b.xpath("following-sibling::blockquote/*"):
                if tag.tag == 'b':
                    text = tag.text
                    if text.startswith('Ayes'):
                        vtype = 'yes'
                        yes_count += int(re.search(
                            r'\((\d+)\):', text).group(1))
                    elif text.startswith('Nays'):
                        vtype = 'no'
                        no_count += int(re.search(
                            r'\((\d+)\):', text).group(1))
                    elif (text.startswith('Excused') or
                          text.startswith('Abstain') or
                          text.startswith('Absent')
                         ):
                        vtype = 'other'
                        other_count += int(re.search(
                            r'\((\d+)\):', text).group(1))
                    else:
                        raise ValueError('bad vote type: %s' % tag.text)
                elif tag.tag == 'a':
                    name = tag.text.strip()
                    if vtype == 'yes':
                        yes_votes.append(name)
                    elif vtype == 'no':
                        no_votes.append(name)
                    elif vtype == 'other':
                        other_votes.append(name)

            passed = yes_count > (no_count + other_count)

            vote = Vote('upper', date, '%s Committee Vote' % committee,
                        passed, yes_count, no_count, other_count)

            for name in yes_votes:
                vote.yes(name)
            for name in no_votes:
                vote.no(name)
            for name in other_votes:
                vote.other(name)

            vote.add_source(self.url)
            self.bill.add_vote(vote)

    def build_versions(self):
        xpath = '//*[contains(., "Versions")]'
        text = self.urls.senate.xpath(xpath)[-1].text_content()
        version_text = re.sub('Versions:?\s*', '', text)

        url_tmpl = 'http://open.nysenate.gov/legislation/bill/'
        for version_bill_id in re.findall('\S+', version_text):
            version_bill_id_noyear, _ = version_bill_id.rsplit('-')
            version_url = url_tmpl + version_bill_id
            self.bill.add_version(version_bill_id_noyear, version_url,
                                  mimetype='text/html')
