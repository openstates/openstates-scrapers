# -*- coding: utf-8 -*-
import re
import os
import datetime
import lxml.html

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

def group(lst, n):
    # from http://code.activestate.com/recipes/303060-group-a-list-into-sequential-n-tuples/
    for i in range(0, len(lst), n):
        val = lst[i:i+n]
        if len(val) == n:
            yield tuple(val)


# chamber prefix, doc id, session_id
LEGISLATION_URL = ('http://ilga.gov/legislation/grplist.asp?num1=1&num2=10000&'
                   'DocTypeID=%s%s&SessionID=%s')

TITLE_REMOVING_PATTERN = re.compile(".*(Rep|Sen). (.+)$")
SPONSOR_PATTERN = re.compile("^(Added |Removed )?(.+Sponsor) (Rep|Sen). (.+)$")

DOC_TYPES = {
    'B': 'bill',
    'R': 'resolution',
    'JR': 'joint resolution',
    'JRCA': 'constitutional amendment',
}

class ILBillScraper(BillScraper):

    state = 'il'


    def scrape(self, chamber, session):
        session_id = self.metadata['session_details'][session]['session_id']
        chamber_slug = 'H' if chamber == 'lower' else 'S'


        for doc_type in DOC_TYPES:
            url = LEGISLATION_URL % (chamber_slug, doc_type, session_id)
            html = self.urlopen(url)
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            for bill_url in doc.xpath('//li/a/@href'):
                self.scrape_bill(chamber, session, chamber_slug+doc_type,
                                 bill_url)


    def scrape_bill(self, chamber, session, doc_type, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        # bill id, title, synopsis
        bill_num = re.findall('DocNum=(\d+)', url)[0]
        bill_type = DOC_TYPES[doc_type[1:]]
        bill_id = doc_type + bill_num

        title = doc.xpath('//span[text()="Short Description:"]/following-sibling::span[1]/text()')[0].strip()
        synopsis = doc.xpath('//span[text()="Synopsis As Introduced"]/following-sibling::span[1]/text()')[0].strip()

        bill = Bill(session, chamber, bill_id, title, type=bill_type,
                    synopsis=synopsis)

        # sponsors
        for sponsor in doc.xpath('//a[@class="content"]/text()'):
            bill.add_sponsor('cosponsor', sponsor)

        # actions
        action_tds = doc.xpath('//a[@name="actions"]/following-sibling::table[1]/td')
        for date, actor, action in group(action_tds, 3):
            date = datetime.datetime.strptime(date.text_content().strip(),
                                              "%m/%d/%Y")
            actor = actor.text_content()
            if actor == 'House':
                actor = 'lower'
            elif actor == 'Senate':
                actor = 'upper'

            action = action.text_content()

            # TODO: categorize actions

            bill.add_action(actor, action, date)

        # versions
        version_url = doc.xpath('//a[text()="Full Text"]/@href')[0]
        self.scrape_documents(bill, version_url)

        votes_url = doc.xpath('//a[text()="Votes"]/@href')[0]
        self.scrape_votes(bill, votes_url)

        bill.add_source(url)
        bill.add_source(votes_url)
        self.save_bill(bill)


    def scrape_documents(self, bill, version_url):
        html = self.urlopen(version_url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(version_url)

        for link in doc.xpath('//a[contains(@href, "fulltext")]'):
            name = link.text
            url = link.get('href')
            if name in ('Introduced', 'Engrossed', 'Enrolled'):
                bill.add_version(name, url)
            elif 'Amendment' in name:
                bill.add_document(name, url)
            elif 'Printer-Friendly' in name:
                pass
            else:
                self.warning('unknown document type %s' % name)


    def scrape_votes(self, bill, votes_url):
        html = self.urlopen(votes_url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(votes_url)

        EXPECTED_VOTE_CODES = ['Y','N','E','NV','A','P','-']

        # vote indicator, a few spaces, a name, newline or multiple spaces
        VOTE_RE = re.compile('(Y|N|E|NV|A|P|-)\s{2,5}(\w.+?)(?:\n|\s{2})')

        for link in doc.xpath('//a[contains(@href, "votehistory")]'):
            _, motion, date = link.text.split(' - ')

            chamber = link.xpath('../following-sibling::td/text()')[0]
            if chamber == 'HOUSE':
                chamber = 'lower'
            elif chamber == 'SENATE':
                chamber = 'upper'
            else:
                self.warning('unknown chamber %s' % chamber)

            date = datetime.datetime.strptime(date, "%A, %B %d, %Y")

            # download the file
            fname, resp = self.urlretrieve(link.get('href'))
            pdflines = convert_pdf(fname, 'text').splitlines()
            os.remove(fname)

            vote = Vote(chamber, date, motion.strip(), False, 0, 0, 0)

            for line in pdflines:
                for match in VOTE_RE.findall(line):
                    vcode, name = match
                    if vcode == 'Y':
                        vote.yes(name)
                    elif vcode == 'N':
                        vote.no(name)
                    else:
                        vote.other(name)

            # fake the counts
            vote['yes_count'] = len(vote['yes_votes'])
            vote['no_count'] = len(vote['no_votes'])
            vote['other_count'] = len(vote['other_votes'])
            vote['passed'] = vote['yes_count'] > vote['no_count']
            vote.add_source(link.get('href'))

            bill.add_vote(vote)
