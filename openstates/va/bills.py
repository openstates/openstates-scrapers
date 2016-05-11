import re
import datetime
from collections import defaultdict

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import lxml.html


BASE_URL = 'http://lis.virginia.gov'

class VABillScraper(BillScraper):
    jurisdiction = 'va'

    vote_strip_re = re.compile(r'(.+)\((\d{1,2})-Y (\d{1,2})-N( (\d{1,2})-A)?\)')
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

    def accept_response(self, response):
        # check for rate limit pages
        normal = super(VABillScraper, self).accept_response(response)
        return (normal and
                'Sorry, your query could not be processed' not in response.text
                and 'the source database is temporarily unavailable' not in response.text)

    def get_page_bills(self, issue_name, href):
        issue_html = self.get('http://lis.virginia.gov' + href,
                                  retry_on_404=True).text
        idoc = lxml.html.fromstring(issue_html)
        for ilink in idoc.xpath(self.link_xpath):
            self.subject_map[ilink.text].append(issue_name)

        more_links = idoc.xpath('//a/b[text()="More..."]/../@href')
        if more_links:
            self.get_page_bills(issue_name, more_links[0])

    def build_subject_map(self):
        url = 'http://lis.virginia.gov/cgi-bin/legp604.exe?%s+sbj+SBJ' % self.site_id
        self.subject_map = defaultdict(list)

        # loop over list of all issue pages
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        for link in doc.xpath(self.link_xpath):
            # get bills from page
            self.get_page_bills(link.text, link.get('href'))


    def scrape(self, chamber, session):
        self.user_agent = 'openstates +mozilla'
        # internal id for the session, store on self so all methods have access
        self.site_id = self.metadata['session_details'][session]['site_id']

        self.build_subject_map()

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
                    self.fetch_sponsors(bill)
                    self.scrape_bill_details(bill_url, bill)
                    bill['subjects'] = self.subject_map[bill_id]
                    bill.add_source(bill_url)
                    self.save_bill(bill)


    def scrape_bill_details(self, url, bill):
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
        for ali in doc.xpath('//h4[text()="HISTORY"]/following-sibling::ul[1]/li'):
            date, action = ali.text_content().split(u' \xa0')
            actor, action = action.split(': ', 1)

            actor = self.actor_map[actor]
            date = datetime.datetime.strptime(date.strip(), '%m/%d/%y')

            # if action ends in (##-Y ##-N) remove that part
            vrematch = self.vote_strip_re.match(action)
            if vrematch:
                action, y, n = vrematch.groups()
                vote = Vote(actor, date, action, int(y) > int(n),
                            int(y), int(n), 0)
                vote_url = ali.xpath('a/@href')
                if vote_url:
                    self.parse_vote(vote, vote_url[0])
                    vote.add_source(BASE_URL + vote_url[0])
                # set other count, it isn't provided
                vote['other_count'] = len(vote['other_votes'])
                #vote.validate()
                bill.add_vote(vote)


            # categorize actions
            for pattern, atype in self._action_classifiers:
                if re.match(pattern, action):
                    break
            else:
                atype = 'other'

            # if matched a 'None' atype, don't add the action
            if atype:
                bill.add_action(actor, action, date, type=atype)


    def fetch_sponsors(self, bill):
        url = "http://lis.virginia.gov/cgi-bin/legp604.exe?%s+mbr+%s" % (
            self.site_id, bill['bill_id'].replace(' ', ''))

        # order of chamber uls
        #if bill['chamber'] == 'lower':
        #    order = ['lower', 'upper']
        #else:
        #    order = ['upper', 'lower']

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

    def split_vote(self, block):
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

    def parse_vote(self, vote, url):
        url = BASE_URL + url

        html = self.get(url, retry_on_404=True).text
        doc = lxml.html.fromstring(html)

        yeas = doc.xpath('//p[contains(text(), "YEAS--")]')
        nays = doc.xpath('//p[contains(text(), "NAYS--")]')
        absts = doc.xpath('//p[contains(text(), "ABSTENTIONS")]')
        #no_votes = doc.xpath('//p[contains(text(), "NOT VOTING")]')[0].text

        map(vote.yes, self.split_vote(yeas))
        map(vote.no, self.split_vote(nays))
        map(vote.other, self.split_vote(absts))
        # don't count not voting as anything?
        #map(vote.other, self.split_vote(no_votes))
