import re
import datetime

from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
import lxml.html

BASE_URL = 'http://leg6.state.va.us'

class VABillScraper(BillScraper):
    state = 'va'

    vote_strip_re = re.compile(r'(.+)\((\d{1,2})-Y (\d{1,2})-N\)')
    actor_map = {'House': 'lower', 'Senate': 'upper', 'Governor': 'governor'}

    def scrape(self, chamber, session):
        # internal id for the session, store on self so all methods have access
        self.site_id = self.metadata['session_details'][session]['site_id']

        # used for skipping bills from opposite chamber
        start_letter = 'H' if chamber == 'lower' else 'S'

        url = 'http://leg6.state.va.us/cgi-bin/legp604.exe?%s+lst+ALL' % self.site_id

        while url:
            with self.urlopen(url) as html:
                doc = lxml.html.fromstring(html)

                url = None  # no more unless we encounter 'More...'

                bills = doc.xpath('//ul[@class="linkSect"]/li')
                for bill in bills:
                    link = bill.getchildren()[0]
                    bill_id = link.text_content()

                    # check if this is the 'More...' link
                    if bill_id == 'More...':
                        url = BASE_URL + link.get('href')

                    # skip bills from the other chamber
                    elif not bill_id.startswith(start_letter):
                        continue

                    else:
                        # create a bill
                        desc = bill.xpath('text()')[0].strip()
                        bill = Bill(session, chamber, bill_id, desc)

                        bill_url = BASE_URL + link.get('href')
                        self.fetch_sponsors(bill)
                        self.scrape_bill_details(bill_url, bill)
                        self.save_bill(bill)


    def scrape_bill_details(self, url, bill):
        #url = "http://leg6.state.va.us/cgi-bin/legp604.exe?%s+sum+%s" % (
        #    self.site_id, bill.replace(' ', '')
        #)
        with self.urlopen(url) as html:
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

                bill.add_version(desc, link, date=date)

            # actions
            for ali in doc.xpath('//h4[text()="HISTORY"]/following-sibling::ul[1]/li'):
                date, action = ali.text_content().split(u' \xa0')
                actor, action = action.split(': ', 1)

                actor = self.actor_map[actor]
                date = datetime.datetime.strptime(date, '%m/%d/%y')

                # if action ends in (##-Y ##-N) remove that part
                vrematch = self.vote_strip_re.match(action)
                if vrematch:
                    action, y, n = vrematch.groups()
                    vote = Vote(actor, date, action, y>n, int(y), int(n), 0)
                    vote_url = ali.xpath('a/@href')
                    if vote_url:
                        self.parse_vote(vote, vote_url[0])
                    bill.add_vote(vote)

                bill.add_action(actor, action, date)


    def fetch_sponsors(self, bill):
        url = "http://leg6.state.va.us/cgi-bin/legp604.exe?%s+mbr+%s" % (
            self.site_id, bill['bill_id'].replace(' ', ''))

        # order of chamber uls
        #if bill['chamber'] == 'lower':
        #    order = ['lower', 'upper']
        #else:
        #    order = ['upper', 'lower']

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for slist in doc.xpath('//ul[@class="linkSect"]'):
                # note that first ul is origin chamber
                for sponsor in slist.xpath('li'):
                    name = sponsor.text_content().strip()
                    if name.endswith(u' (chief\xa0patron)'):
                        name = name[:-15]
                        type = 'primary'
                    else:
                        type = 'cosponsor'
                    bill.add_sponsor(name, type)

    def split_vote(self, block):
        if block:
            block = block[0].text

            pieces = block.split('--')
            # if there are only two pieces, there are no abstentions
            if len(pieces) <= 2:
                return []
            else:
                return [x.strip() for x in pieces[1].split(', ')]
        else:
            return []

    def parse_vote(self, vote, url):
        url = BASE_URL + url

        with self.urlopen(url) as html:
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
