# -*- coding: utf-8 -*-
import re
import datetime
import lxml.html

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import votes

def standardize_chamber(s):
    if s is not None:
        if s.lower() == 'house':
            return 'lower'
        if s.lower() == 'senate':
            return 'upper'
    return s

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
        version_url = doc.xpath('//a[text()="Full Text"]')[0].get('href')
        self.scrape_documents(bill, version_url)

        bill.add_source(url)
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


    def apply_votes(self, bill):
        """Given a bill (and assuming it has a status_url in its dict), parse all of the votes
        """
        bill_votes = votes.all_votes_for_url(self, bill['status_url'])
        for (chamber,vote_desc,pdf_url,these_votes) in bill_votes:
            try:
                date = vote_desc.split("-")[-1]
            except IndexError:
                self.warning("[%s] Couldn't get date out of [%s]" % (bill['bill_id'],vote_desc))
                continue
            yes_votes = []
            no_votes = []
            other_votes = []
            for voter,vote in these_votes.iteritems():
                if vote == 'Y':
                    yes_votes.append(voter)
                elif vote == 'N':
                    no_votes.append(voter)
                else:
                    other_votes.append(voter)
            passed = len(yes_votes) > len(no_votes) # not necessarily correct, but not sure where else to get it. maybe from pdf
            vote = Vote(standardize_chamber(chamber),date,vote_desc,passed, len(yes_votes), len(no_votes), len(other_votes),pdf_url=pdf_url)
            for voter in yes_votes:
                vote.yes(voter)
            for voter in no_votes:
                vote.no(voter)
            for voter in other_votes:
                vote.other(voter)
            bill.add_vote(vote)
