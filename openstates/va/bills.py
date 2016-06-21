import re
import datetime
from collections import defaultdict

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import lxml.html


BASE_URL = 'http://lis.virginia.gov'


class VABillScraper(BillScraper):
    jurisdiction = 'va'

    # There's a weird catch-all for numerals after the dash in the Yes
    # count. That's because we've actually encountered this.
    vote_strip_re = re.compile(r'(.+)\((\d+)-[\d]*Y (\d+)-N(?: (\d+)-A)?\)')
    actor_map = {'House': 'lower', 'Senate': 'upper', 'Governor': 'governor',
                 'Conference': 'conference'}

    _action_classifiers = (
        ('Approved by Governor', 'governor:signed'),
        ('\s*Amendment(s)? .+ agreed', 'amendment:passed'),
        ('\s*Amendment(s)? .+ withdrawn', 'amendment:withdrawn'),
        ('\s*Amendment(s)? .+ rejected', 'amendment:failed'),
        ('Subject matter referred', 'committee:referred'),
        ('Rereferred to', 'committee:referred'),
        ('Referred to', 'committee:referred'),
        ('Assigned ', 'committee:referred'),
        ('Reported from', 'committee:passed'),
        ('Read third time and passed', ['bill:passed', 'bill:reading:3']),
        ('Read third time and agreed', ['bill:passed', 'bill:reading:3']),
        ('Passed (Senate|House)', 'bill:passed'),
        ('Read third time and defeated', 'bill:failed'),
        ('Presented', 'bill:introduced'),
        ('Prefiled and ordered printed', 'bill:introduced'),
        ('Read first time', 'bill:reading:1'),
        ('Read second time', 'bill:reading:2'),
        ('Read third time', 'bill:reading:3'),
        ('Senators: ', None),
        ('Delegates: ', None),
        ('Committee substitute printed', None),
        ('Bill text as passed', None),
        ('Acts of Assembly', None),
    )

    link_xpath = '//ul[@class="linkSect"]/li/a'

    def _accept_response(self, response):
        # check for rate limit pages
        normal = super(VABillScraper, self)._accept_response(response)
        return (normal and
            'Sorry, your query could not be processed' not in response.text
            and 'the source database is temporarily unavailable' not in response.text)

    def _get_page_bills(self, issue_name, href):
        issue_html = self.get('http://lis.virginia.gov' + href,
                                  retry_on_404=True).text
        idoc = lxml.html.fromstring(issue_html)
        for ilink in idoc.xpath(self.link_xpath):
            self.subject_map[ilink.text].append(issue_name)

        more_links = idoc.xpath('//a/b[text()="More..."]/../@href')
        if more_links:
            self._get_page_bills(issue_name, more_links[0])

    def _build_subject_map(self):
        url = 'http://lis.virginia.gov/cgi-bin/legp604.exe?%s+sbj+SBJ' % self.site_id
        self.subject_map = defaultdict(list)

        # loop over list of all issue pages
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        for link in doc.xpath(self.link_xpath):
            # get bills from page
            self._get_page_bills(link.text, link.get('href'))

    def _fetch_sponsors(self, bill):
        url = "http://lis.virginia.gov/cgi-bin/legp604.exe?%s+mbr+%s" % (
            self.site_id, bill['bill_id'].replace(' ', ''))

        html = self.get(url, retry_on_404=True).text
        doc = lxml.html.fromstring(html)

        for slist in doc.xpath('//ul[@class="linkSect"]'):
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
                bill.add_sponsor(type, name)

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
                return [x.strip() for x in re.split('(?<!Bell), (?!\w\.\w?\.?)', pieces[1]) if x.strip()]
        else:
            return []

    def _parse_vote(self, vote, url):
        url = BASE_URL + url

        html = self.get(url, retry_on_404=True).text
        doc = lxml.html.fromstring(html)

        yeas = doc.xpath('//p[contains(text(), "YEAS--")]')
        nays = doc.xpath('//p[contains(text(), "NAYS--")]')
        # We capture "other" types of votes separately just in case we
        # want to have the granularity later.
        rule36 = doc.xpath('//p[contains(text(), "RULE 36--")]')
        abstaining = doc.xpath('//p[contains(text(), "ABSTENTIONS--")]')
        notvoting = doc.xpath('//p[contains(text(), "NOT VOTING--")]')

        map(vote.yes, self._split_vote(yeas))
        map(vote.no, self._split_vote(nays))
        # Flattening all types of other votes into a single list.
        other_votes = []
        map(other_votes.extend, (self._split_vote(rule36), self._split_vote(abstaining),
            self._split_vote(notvoting)))
        map(vote.other, other_votes)

    def _scrape_bill_details(self, url, bill):
        html = self.get(url, retry_on_404=True).text
        doc = lxml.html.fromstring(html)

        # summary sections
        summary = doc.xpath('//h4[starts-with(text(), "SUMMARY")]/following-sibling::p/text()')
        if summary and summary[0].strip():
            bill['summary'] = summary[0].strip()

        # versions
        for va in doc.xpath('//h4[text()="FULL TEXT"]/following-sibling::ul[1]/li/a[1]'):

            # 11/16/09 \xa0House: Prefiled and ordered printed; offered 01/13/10 10100110D
            date, desc = va.text.split(u' \xa0')
            desc.rsplit(' ', 1)[0]              # chop off last part
            link = va.get('href')
            date = datetime.datetime.strptime(date, '%m/%d/%y')

            # budget bills in VA are searchable but no full text available
            if '+men+' in link:
                self.warning('not adding budget version, bill text not available')
            else:
                # VA duplicates reprinted bills, lets keep the original name
                bill.add_version(desc, BASE_URL+link, date=date,
                                 mimetype='text/html',
                                 on_duplicate='use_old')

        # actions
        cached_vote = None
        cached_action = None
        for ali in doc.xpath('//h4[text()="HISTORY"]/following-sibling::ul[1]/'
            'li'):
            vote = None

            date, action = ali.text_content().split(u' \xa0')
            actor, action = action.split(': ', 1)

            # Bill history entries purely in parentheses tend to be
            # notes and not actions, so we'll skip them.
            if action.startswith('(') and action.endswith(')'):
                continue

            actor = self.actor_map[actor]
            date = datetime.datetime.strptime(date.strip(), '%m/%d/%y')

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
                    cached_vote = Vote(actor, date, vote_action, y > n, y, n,
                        o)
                    if vote_url:
                        cached_vote.add_source(BASE_URL + vote_url[0])
                    continue
                elif cached_vote is not None:
                    if vote_action.startswith(u'VOTE:'):
                        if (vote_url
                            and cached_vote['yes_count'] == y
                            and cached_vote['no_count'] == n
                            and cached_vote['other_count'] == o):
                            vote = cached_vote
                            self._parse_vote(vote, vote_url[0])
                            vote.add_source(BASE_URL + vote_url[0])
                            action = cached_action
                    elif cached_vote['motion'].startswith('VOTE:'):
                        if (cached_vote['yes_count'] == y
                            and cached_vote['no_count'] == n
                            and cached_vote['other_count'] == o):
                            vote = cached_vote
                            vote['motion'] = vote_action
                    else:
                        # Cached vote doesn't match up to the current
                        # one. Save, then cache the current vote to
                        # begin the next search.
                        bill.add_vote(cached_vote)
                        cached_vote = Vote(actor, date, vote_action, y > n, y,
                            n, o)
                        if vote_url:
                            cached_vote.add_source(BASE_URL + vote_url[0])
                        cached_action = action
                        continue

                if vote is None:
                    raise ValueError('Cannot save an empty vote.')
                #vote.validate()
                bill.add_vote(vote)
            else:
                # If this action isn't a vote, but the last one was,
                # there's obviously no additional vote data to match.
                # Go ahead and save the cached data.
                if cached_vote is not None:
                    bill.add_vote(cached_vote)

            cached_vote = cached_action = None

            # categorize actions
            for pattern, atype in self._action_classifiers:
                if re.match(pattern, action):
                    break
            else:
                atype = 'other'

            # if matched a 'None' atype, don't add the action
            if atype:
                bill.add_action(actor, action, date, type=atype)


    def scrape(self, chamber, session):
        self.user_agent = 'openstates +mozilla'
        # internal id for the session, store on self so all methods have access
        self.site_id = self.metadata['session_details'][session]['site_id']

        self._build_subject_map()

        # used for skipping bills from opposite chamber
        start_letter = 'H' if chamber == 'lower' else 'S'

        url = 'http://lis.virginia.gov/cgi-bin/legp604.exe?%s+lst+ALL' % self.site_id

        while url:
            html = self.get(url, retry_on_404=True).text
            doc = lxml.html.fromstring(html)

            url = None  # no more unless we encounter 'More...'

            bills = doc.xpath('//ul[@class="linkSect"]/li')
            for bill in bills:
                link = bill.getchildren()[0]
                bill_id = str(link.text_content())

                # check if this is the 'More...' link
                if bill_id.startswith('More'):
                    url = BASE_URL + link.get('href')

                # skip bills from the other chamber
                elif not bill_id.startswith(start_letter):
                    continue

                else:
                    # create a bill
                    desc = bill.xpath('text()')[0].strip()
                    bill_type = {'B': 'bill',
                                 'J': 'joint resolution',
                                 'R': 'resolution'}[bill_id[1]]
                    bill = Bill(session, chamber, bill_id, desc,
                                type=bill_type)

                    bill_url = BASE_URL + link.get('href')
                    self._fetch_sponsors(bill)
                    self._scrape_bill_details(bill_url, bill)
                    bill['subjects'] = self.subject_map[bill_id]
                    bill.add_source(bill_url)
                    self.save_bill(bill)
