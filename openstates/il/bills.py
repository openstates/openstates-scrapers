# -*- coding: utf-8 -*-
import re
import os
import datetime
import lxml.html
from urllib import urlencode

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

def group(lst, n):
    # from http://code.activestate.com/recipes/303060-group-a-list-into-sequential-n-tuples/
    for i in range(0, len(lst), n):
        val = lst[i:i+n]
        if len(val) == n:
            yield tuple(val)


TITLE_REMOVING_PATTERN = re.compile(".*(Rep|Sen). (.+)$")
SPONSOR_PATTERN = re.compile("^(Added |Removed )?(.+Sponsor) (Rep|Sen). (.+)$")

VERSION_TYPES = ('Introduced', 'Engrossed', 'Enrolled', 'Re-Enrolled')
FULLTEXT_DOCUMENT_TYPES = ('Public Act',)
DOC_TYPES = {
    'B': 'bill',
    'R': 'resolution',
    'JR': 'joint resolution',
    'JRCA': 'constitutional amendment',
}

_action_classifiers = (
    ('Amendment No. \d+ Filed', 'amendment:introduced'),
    ('Amendment No. \d+ Tabled', 'amendment:failed'),
    ('Amendment No. \d+ Adopted', 'amendment:passed'),
    ('(Pref|F)iled with', 'bill:filed'),
    ('Arrived? in', 'bill:introduced'),
    ('First Reading', 'bill:reading:1'),
    ('(Recalled to )?Second Reading', 'bill:reading:2'),
    ('(Re-r|R)eferred to', 'committee:referred'),
    ('(Re-a|A)ssigned to', 'committee:referred'),
    ('Sent to the Governor', 'governor:received'),
    ('Governor Approved', 'governor:signed'),
    ('Governor Vetoed', 'governor:vetoed'),
    ('Governor Item', 'governor:vetoed:line-item'),
    ('Governor Amendatory Veto', 'governor:vetoed'),
    ('Do Pass', 'committee:passed'),
    ('Recommends Be Adopted', 'committee:passed:favorable'),
    ('Third Reading .+? Passed', ['bill:reading:3', 'bill:passed']),
    ('Third Reading .+? Lost', ['bill:reading:3', 'bill:failed']),
    ('Resolution Adopted', 'bill:passed'),
    ('Resolution Lost', 'bill:failed'),
    ('Tabled', 'bill:withdrawn'),
)


def _categorize_action(action):
    for pattern, atype in _action_classifiers:
        if re.findall(pattern, action):
            return atype
    return 'other'

LEGISLATION_URL = ('http://ilga.gov/legislation/grplist.asp')

def build_url_for_legislation_list(metadata, chamber, session, doc_type):
    base_params = metadata['session_details'][session].get('params',{})
    base_params['num1'] = '1'
    base_params['num2'] = '10000'
    params = dict(base_params)
    params['DocTypeID'] = '%s%s' % (chamber_slug(chamber),doc_type)
    return '?'.join([LEGISLATION_URL,urlencode(params)])

def chamber_slug(chamber):
    if chamber == 'lower':
        return 'H'
    return 'S'

class ILBillScraper(BillScraper):

    state = 'il'

    def get_bill_urls(self, chamber, session, doc_type):
        url = build_url_for_legislation_list(self.metadata, chamber, session, doc_type)
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        for bill_url in doc.xpath('//li/a/@href'):
            yield bill_url
    
    def scrape(self, chamber, session):
        for doc_type in DOC_TYPES:
            for bill_url in self.get_bill_urls(chamber, session, doc_type):
                self.scrape_bill(chamber, session, chamber_slug(chamber)+doc_type, bill_url)
    
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

            bill.add_action(actor, action, date,
                            type=_categorize_action(action))

        # versions
        version_url = doc.xpath('//a[text()="Full Text"]/@href')[0]
        self.scrape_documents(bill, version_url)

        # if there's more than 1 votehistory link, there are votes to grab
        if len(doc.xpath('//a[contains(@href, "votehistory")]')) > 1:
            votes_url = doc.xpath('//a[text()="Votes"]/@href')[0]
            self.scrape_votes(bill, votes_url)
            bill.add_source(votes_url)

        bill.add_source(url)
        self.save_bill(bill)


    def scrape_documents(self, bill, version_url):
        html = self.urlopen(version_url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(version_url)

        for link in doc.xpath('//a[contains(@href, "fulltext")]'):
            name = link.text
            url = link.get('href')
            if name in VERSION_TYPES:
                bill.add_version(name, url)
            elif 'Amendment' in name or name in FULLTEXT_DOCUMENT_TYPES:
                bill.add_document(name, url)
            elif 'Printer-Friendly' in name:
                pass
            else:
                self.warning('unknown document type %s - adding as document' % name)
                bill.add_document(name, url)

    def scrape_votes(self, bill, votes_url):
        html = self.urlopen(votes_url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(votes_url)

        EXPECTED_VOTE_CODES = ['Y','N','E','NV','A','P','-']

        # vote indicator, a few spaces, a name, newline or multiple spaces
        VOTE_RE = re.compile('(Y|N|E|NV|A|P|-)\s{2,5}(\w.+?)(?:\n|\s{2})')

        for link in doc.xpath('//a[contains(@href, "votehistory")]'):

            pieces = link.text.split(' - ')
            date = pieces[-1]
            if len(pieces) == 3:
                motion = pieces[1]
            else:
                motion = 'Third Reading'

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
