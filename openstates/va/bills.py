import re
import pytz
import datetime
import collections
import logging

from spatula import Page, Spatula
from pupa.scrape import Scraper, Bill, VoteEvent
from .common import SESSION_SITE_IDS


tz = pytz.timezone('America/New_York')

BASE_URL = 'http://lis.virginia.gov'
URL_PATTERNS = {
    'list': '/cgi-bin/legp604.exe?{}+lst+ALL',
    'summary': '/cgi-bin/legp604.exe?{}+sum+{}',
    'sponsors': '/cgi-bin/legp604.exe?{}+mbr+{}',
    'subjects': '/cgi-bin/legp604.exe?{}+sbj+SBJ',
}
SKIP = '~~~SKIP~~~'
ACTION_CLASSIFIERS = (
    ('Enacted, Chapter', 'became-law'),
    ('Approved by Governor', 'executive-signature'),
    ('Vetoed by Governor', 'executive-veto'),
    ('(House|Senate) sustained Governor\'s veto', 'veto-override-failure'),
    (r'\s*Amendment(s)? .+ agreed', 'amendment-passage'),
    (r'\s*Amendment(s)? .+ withdrawn', 'amendment-withdrawal'),
    (r'\s*Amendment(s)? .+ rejected', 'amendment-failure'),
    ('Subject matter referred', 'referral-committee'),
    ('Rereferred to', 'referral-committee'),
    ('Referred to', 'referral-committee'),
    ('Assigned ', 'referral-committee'),
    ('Reported from', 'committee-passage'),
    ('Read third time and passed', ['passage', 'reading-3']),
    ('Read third time and agreed', ['passage', 'reading-3']),
    ('Passed (Senate|House)', 'passage'),
    ('passed (Senate|House)', 'passage'),
    ('Read third time and defeated', 'failure'),
    ('Presented', 'introduction'),
    ('Prefiled and ordered printed', 'introduction'),
    ('Read first time', 'reading-1'),
    ('Read second time', 'reading-2'),
    ('Read third time', 'reading-3'),
    ('Senators: ', SKIP),
    ('Delegates: ', SKIP),
    ('Committee substitute printed', SKIP),
    ('Bill text as passed', SKIP),
    ('Acts of Assembly', SKIP),
)


class SubjectPage(Page, Spatula):
    def handle_page(self):
        subjects = collections.defaultdict(list)
        for link in self.doc.xpath('//ul[@class="linkSect"]/li/a'):
            for bill_id in self.scrape_page(SubjectBillListPage, url=link.get('href')):
                subjects[bill_id].append(link.text)
        return subjects


class SubjectBillListPage(Page, Spatula):
    def handle_page(self):
        for bill in self.doc.xpath('//ul[@class="linkSect"]/li'):
            link = bill.getchildren()[0]
            yield str(link.text_content())
        next_url = self.doc.xpath('//a/b[text()="More..."]/../@href')
        if next_url:
            yield from self.scrape_page_items(SubjectBillListPage, url=next_url[0])


class BillListPage(Page, Spatula):
    def handle_page(self):
        bills = self.doc.xpath('//ul[@class="linkSect"]/li')
        for bill in bills:
            link = bill.getchildren()[0]
            bill_id = str(link.text_content())

            if not bill_id.startswith(('S', 'H')):
                continue

            # create a bill
            desc = bill.xpath('text()')[0].strip()
            chamber = {
                'H': 'lower',
                'S': 'upper',
            }[bill_id[0]]
            bill_type = {
                'B': 'bill',
                'J': 'joint resolution',
                'R': 'resolution'
            }[bill_id[1]]
            bill = Bill(bill_id, self.kwargs['session'], desc,
                        chamber=chamber, classification=bill_type)

            bill_url = link.get('href')
            sponsor_url = BASE_URL + URL_PATTERNS['sponsors'].format(
                self.kwargs['session_id'],
                bill_id.replace(' ', ''),
            )

            list(self.scrape_page_items(BillSponsorPage, url=sponsor_url, obj=bill))
            yield from self.scrape_page_items(BillDetailPage, url=bill_url, obj=bill)
            bill.subject = self.kwargs['subjects'][bill_id]
            bill.add_source(bill_url)
            yield bill

        next_url = self.doc.xpath('//a/b[text()="More..."]/../@href')
        if next_url:
            yield from self.scrape_page_items(BillListPage, url=next_url[0], **self.kwargs)


class BillSponsorPage(Page, Spatula):
    def handle_page(self):
        for slist in self.doc.xpath('//ul[@class="linkSect"]'):
            # note that first ul is origin chamber
            for sponsor in slist.xpath('li'):
                name = sponsor.text_content().strip()
                if name.endswith(u' (chief\xa0patron)'):
                    name = name[:-15]
                    type = 'primary'
                elif name.endswith(u' (chief\xa0co-patron)'):
                    name = name[:-18]
                    type = 'cosponsor'
                else:
                    type = 'cosponsor'
                self.obj.add_sponsorship(name, type, 'person', type == 'primary')
                yield self.obj


class BillDetailPage(Page, Spatula):

    # There's a weird catch-all for numerals after the dash in the Yes
    # count. That's because we've actually encountered this.
    # There's also a catch-all for dashes before the number in No count
    vote_strip_re = re.compile(r'(.+)\((\d+)-[\d]*Y -?(\d+)-N(?: (\d+)-A)?\)')
    actor_map = {'House': 'lower', 'Senate': 'upper', 'Governor': 'executive',
                 'Conference': 'legislature'}

    def handle_page(self):
        summary = self.doc.xpath('/'.join([
            '//h4[starts-with(text(), "SUMMARY")]',
            '/following-sibling::p',
            'text()',
        ]))
        if summary and summary[0].strip():
            self.obj.add_abstract(abstract=summary[0].strip(), note='summary')

        # versions
        for va in self.doc.xpath('//h4[text()="FULL TEXT"]/following-sibling::ul[1]/li/a[1]'):

            # 11/16/09 \xa0House: Prefiled and ordered printed; offered 01/13/10 10100110D
            date, desc = va.text.split(u' \xa0')
            desc.rsplit(' ', 1)[0]              # chop off last part
            link = va.get('href')
            if 'http' not in link:
                link = '{}{}'.format(BASE_URL, link)
            date = datetime.datetime.strptime(date, '%m/%d/%y').date()

            # budget bills in VA are searchable but no full text available
            if '+men+' in link:
                logging.getLogger('va').warning(
                    'not adding budget version, bill text not available'
                )
            else:
                # VA duplicates reprinted bills, lets keep the original name
                self.obj.add_version_link(desc, link, date=date,
                                          media_type='text/html',
                                          on_duplicate='ignore')

        # amendments
        for va in self.doc.xpath('//h4[text()="AMENDMENTS"]/following-sibling::ul[1]/li/a[1]'):
            version_name = va.xpath('string(.)')
            if ('adopted' in version_name.lower() \
                    or 'engrossed' in version_name.lower()) \
                    and 'not adopted' not in version_name.lower() \
                    and 'not engrossed' not in version_name.lower():
                version_url = va.xpath('@href')[0]
                self.obj.add_version_link(version_name, version_url,
                                          media_type='text/html',
                                          on_duplicate='ignore')

        # actions
        cached_vote = None
        cached_action = None
        for ali in self.doc.xpath('//h4[text()="HISTORY"]/following-sibling::ul[1]/li'):
            vote = None

            date, action = ali.text_content().split(u' \xa0')
            try:
                actor, action = action.split(': ', 1)
            except ValueError:
                assert any([action.startswith('{}:'.format(x)) for x in self.actor_map.keys()]), \
                        "Unparseable action text found: '{}'".format(action)
                logging.getLogger('va').warning(
                    "Skipping apparently-null action: '{}'".format(action)
                )
                continue

            # Bill history entries purely in parentheses tend to be
            # notes and not actions, so we'll skip them.
            if action.startswith('(') and action.endswith(')'):
                continue

            actor = self.actor_map[actor]
            date = datetime.datetime.strptime(date.strip(), '%m/%d/%y').date()

            # if action ends in (##-Y ##-N) remove that part
            vrematch = self.vote_strip_re.match(action)
            # The following conditional logic is messy to handle
            # Virginia's crazy and inconsistently formatted bill
            # histories. Someone less harried and tired than me
            # could probably make this much cleaner. - alo
            if vrematch:
                vote_action, y, n, o = vrematch.groups()
                y = int(y)
                n = int(n)
                # Set default count for "other" votes to 0. We have to
                # do this explicitly as it's excluded from the action
                # text when there were no abstentions (the only type of
                # "other" vote encountered thus far).
                if o is None:
                    o = 0
                else:
                    o = int(o)

                vote_url = ali.xpath('a/@href')

                # Caches relevant information from the current action if
                # vote count encountered, then searches for the presence
                # of identical counts in the next entry (we assume that
                # it's probably there). If matching votes are found, it
                # pulls the cached data to create a unified vote record.
                #
                # This is because Virginia usually publishes two lines
                # of history data for a single vote, without guaranteed
                # order, so we cache and unsafely attempt to match on
                # identical vote counts in the next line.
                if cached_vote is None:
                    cached_action = action
                    cached_vote = VoteEvent(
                        start_date=date,
                        chamber=actor,
                        motion_text=vote_action,
                        result='pass' if y > n else 'fail',
                        classification='passage',
                        bill=self.obj,
                    )
                    cached_vote.set_count('yes', y)
                    cached_vote.set_count('no', n)
                    cached_vote.set_count('other', o)
                    if vote_url:
                        list(self.scrape_page_items(VotePage, url=vote_url[0], obj=cached_vote))
                        cached_vote.add_source(vote_url[0])
                    else:
                        cached_vote.add_source(self.url)
                    continue
                elif cached_vote is not None:
                    if vote_action.startswith(u'VOTE:'):
                        counts = {count['option']: count['value'] for count in cached_vote.counts}
                        if (vote_url and
                                counts['yes'] == y and
                                counts['no'] == n and
                                counts['other'] == o):
                            vote = cached_vote
                            vote.add_source(vote_url[0])
                            action = cached_action
                    elif cached_vote.motion_text.startswith('VOTE:'):
                        counts = {count['option']: count['value'] for count in cached_vote.counts}
                        if (counts['yes'] == y and
                                counts['no'] == n and
                                counts['other'] == o):
                            vote = cached_vote
                            vote.motion_text = vote_action
                    else:
                        # Cached vote doesn't match up to the current
                        # one. Save, then cache the current vote to
                        # begin the next search.
                        yield from add_pupa_id(cached_vote)
                        cached_vote = VoteEvent(
                            start_date=date,
                            chamber=actor,
                            motion_text=vote_action,
                            result='pass' if y > n else 'fail',
                            classification='passage',
                            bill=self.obj,
                        )
                        cached_vote.set_count('yes', y)
                        cached_vote.set_count('no', n)
                        cached_vote.set_count('other', o)
                        if vote_url:
                            cached_vote.add_source(vote_url[0])
                            list(self.scrape_page_items(
                                VotePage, url=vote_url[0], obj=cached_vote))
                        else:
                            cached_vote.add_source(self.url)
                        cached_action = action
                        continue

                if vote is not None:
                    yield from add_pupa_id(vote)
            else:
                # If this action isn't a vote, but the last one was,
                # there's obviously no additional vote data to match.
                # Go ahead and save the cached data.
                if cached_vote is not None:
                    yield from add_pupa_id(cached_vote)

            cached_vote = cached_action = None

            # categorize actions
            for pattern, atype in ACTION_CLASSIFIERS:
                if re.match(pattern, action):
                    break
            else:
                atype = None

            # if matched a 'None' atype, don't add the action
            if atype != SKIP:
                self.obj.add_action(action, date,
                                    chamber=actor,
                                    classification=atype)


class VotePage(Page):
    def handle_page(self):
        yeas = self.doc.xpath('//p[contains(text(), "YEAS--")]')
        nays = self.doc.xpath('//p[contains(text(), "NAYS--")]')
        # We capture "other" types of votes separately just in case we
        # want to have the granularity later.
        rule36 = self.doc.xpath('//p[contains(text(), "RULE 36--")]')
        abstaining = self.doc.xpath('//p[contains(text(), "ABSTENTIONS--")]')
        notvoting = self.doc.xpath('//p[contains(text(), "NOT VOTING--")]')

        for name in self._split_vote(yeas):
            self.obj.vote('yes', name)
        for name in self._split_vote(nays):
            self.obj.vote('no', name)
        # Flattening all types of other votes into a single list.
        other_votes = []
        map(other_votes.extend, (self._split_vote(rule36), self._split_vote(abstaining),
            self._split_vote(notvoting)))
        for name in other_votes:
            self.obj.vote('other', name)
        yield self.obj

    def _split_vote(self, block):
        if block:
            block = block[0].text.replace('\r\n', ' ')

            pieces = block.split('--')
            # if there are only two pieces, there are no abstentions
            if len(pieces) <= 2:
                return []
            else:
                # lookahead and don't split if comma precedes initials
                # Also, Bell appears as Bell, Richard B. and Bell, Robert P.
                # and so needs the lookbehind assertion.
                return [
                    x.strip()
                    for x in re.split(r'(?<!Bell), (?!\w\.\w?\.?)', pieces[1])
                    if x.strip()
                ]
        else:
            return []


_seen_pupa_ids = set()


def add_pupa_id(vote):
    """ adds a distinct pupa_id to a vote based on the unique vote URL """
    for source in vote.sources:
        if '+vot+' in source['url']:
            vote.pupa_id = source['url']
            break
    else:
        vote.pupa_id = None

    if vote.pupa_id in _seen_pupa_ids:
        # skip over votes we've already seen
        return
    else:
        _seen_pupa_ids.add(vote.pupa_id)
        yield vote


class VaBillScraper(Scraper, Spatula):
    def scrape(self, session=None):
        if not session:
            session = self.jurisdiction.legislative_sessions[-1]['identifier']
            self.info('no session specified, using %s', session)
        session_id = SESSION_SITE_IDS[session]
        url = BASE_URL + URL_PATTERNS['list'].format(session_id)
        subject_url = BASE_URL + URL_PATTERNS['subjects'].format(session_id)
        subjects = self.scrape_page(SubjectPage, url=subject_url)
        yield from self.scrape_page_items(BillListPage, url=url, session=session,
                                          session_id=session_id, subjects=subjects)

    def accept_response(self, response):
        # check for rate limit pages
        normal = super().accept_response(response)
        return (normal and
                'Sorry, your query could not be processed' not in response.text and
                'the source database is temporarily unavailable' not in response.text)
