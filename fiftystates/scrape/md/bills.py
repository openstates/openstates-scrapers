#!/usr/bin/env python
import datetime
import itertools
import re

import lxml.html
from scrapelib import HTTPError

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.md import metadata

CHAMBERS = {
    'upper': ('SB','SJ'),
    'lower': ('HB','HJ'),
}

classifiers = {
    r'Committee Amendment .+? Adopted': 'amendment:passed',
    r'Favorable': 'committee:passed:favorable',
    r'First Reading': 'committee:referred',
    r'Floor (Committee )?Amendment\s?\(.+?\)$': 'amendment:introduced',
    r'Floor Amendment .+? Rejected': 'amendment:failed',
    r'Floor (Committee )?Amendment .+? Adopted': 'amendment:passed',
    r'Floor Amendment .+? Withrdawn': 'amendment:withdrawn',
    r'Pre\-filed': 'bill:introduced',
    r'Re\-(referred|assigned)': 'committee:referred',
    r'Recommit to Committee': 'committee:referred',
    r'Third Reading Passed': 'bill:passed',
    r'Third Reading Failed': 'bill:failed',
    r'Unfavorable': 'committee:passed:unfavorable',
    r'Vetoed': 'veto',
    r'Approved by the Governor': 'bill:signed',
    r'Conference Committee|Passed Enrolled|Special Order|Senate Concur|Motion|Laid Over|Hearing|Committee Amendment|Assigned a chapter': 'other',
}

def _classify_action(action):
    if not action:
        return None

    for regex, type in classifiers.iteritems():
        if re.match(regex, action):
            return type
    return None

BASE_URL = "http://mlis.state.md.us"
BILL_URL = BASE_URL + "/%s/billfile/%s%04d.htm" # year, session, bill_type, number

MOTION_RE = re.compile(r"(?P<motion>[\w\s]+) \((?P<yeas>\d{1,3})-(?P<nays>\d{1,3})\)")

class MDBillScraper(BillScraper):
    state = 'md'

    def parse_bill_sponsors(self, doc, bill):
        sponsor_list = doc.cssselect('a[name=Sponlst]')
        if sponsor_list:
            # more than one bill sponsor exists
            elems = sponsor_list[0] \
                .getparent().getparent().getparent().cssselect('dd a')
            for elem in elems:
                bill.add_sponsor('cosponsor', elem.text.strip())
        else:
            # single bill sponsor
            sponsor = doc.cssselect('a[name=Sponsors]')[0] \
                .getparent().getparent().cssselect('dd a')[0].text.strip()
            bill.add_sponsor('primary', sponsor)

    def parse_bill_actions(self, doc, bill):
        for h5 in doc.xpath('//h5'):
            if h5.text == 'House Action':
                chamber = 'lower'
            elif h5.text == 'Senate Action':
                chamber = 'upper'
            elif h5.text == 'Action after passage in Senate and House':
                chamber = 'governor'
            else:
                break
            dts = h5.getnext().xpath('dl/dt')
            for dt in dts:
                action_date = dt.text.strip()
                if action_date != 'No Action':
                    try:
                        action_date = datetime.datetime.strptime(action_date,
                                                                 '%m/%d')
                        action_date = action_date.replace(int(bill['session']))

                        actions = dt.getnext().text_content().split('\r\n')
                        for act in actions:
                            act = act.strip()
                            atype = _classify_action(act)
                            if atype:
                                bill.add_action(chamber, act, action_date,
                                               type=atype)
                    except ValueError:
                        pass # probably trying to parse a bad entry

    def parse_bill_documents(self, doc, bill):
        for elem in doc.cssselect('b'):
            if elem.text:
                doc_type = elem.text.strip().strip(":")
                if doc_type.startswith('Bill Text'):
                    for sib in elem.itersiblings():
                        if sib.tag == 'a':
                            bill.add_version(sib.text.strip(','), BASE_URL + sib.get('href'))
                elif doc_type.startswith('Fiscal and Policy Note'):
                    for sib in elem.itersiblings():
                        if sib.tag == 'a' and sib.text == 'Available':
                            bill.add_document(doc_type, BASE_URL + sib.get('href'))

    def parse_bill_votes(self, doc, bill):
        params = {
            'chamber': bill['chamber'],
            'date': None,
            'motion': None,
            'passed': None,
            'yes_count': None,
            'no_count': None,
            'other_count': None,
        }
        elems = doc.cssselect('a')

        for elem in elems:
            href = elem.get('href')
            if href and "votes" in href and href.endswith('htm'):
                vote_url = BASE_URL + href
                with self.urlopen(vote_url) as vote_html:
                    vote_doc = lxml.html.fromstring(vote_html)
                    # motion
                    for a in vote_doc.cssselect('a'):
                         if 'motions' in a.get('href'):
                            match = MOTION_RE.match(a.text)
                            if match:
                                motion = match.groupdict().get('motion', '').strip()
                                params['passed'] = 'Passed' in motion or 'Adopted' in motion
                                params['motion'] = motion
                                break
                    # ugh
                    bs = vote_doc.cssselect('b')[:5]
                    yeas = int(bs[0].text.split()[0])
                    nays = int(bs[1].text.split()[0])
                    excused = int(bs[2].text.split()[0])
                    not_voting = int(bs[3].text.split()[0])
                    absent = int(bs[4].text.split()[0])
                    params['yes_count'] = yeas
                    params['no_count'] = nays
                    params['other_count'] = excused + not_voting + absent

                    # date
                    # parse the following format: March 23, 2009 8:44 PM
                    (date_elem, time_elem) = vote_doc.cssselect('table td font')[1:3]
                    dt = "%s %s" % (date_elem.text.strip(), time_elem.text.strip())
                    params['date'] = datetime.datetime.strptime(dt, '%B %d, %Y %I:%M %p')

                    vote = Vote(**params)

                    status = None
                    for row in vote_doc.cssselect('table')[3].cssselect('tr'):
                        text = row.text_content()
                        if text.startswith('Voting Yea'):
                            status = 'yes'
                        elif text.startswith('Voting Nay'):
                            status = 'no'
                        elif text.startswith('Not Voting') or text.startswith('Excused'):
                            status = 'other'
                        else:
                            for cell in row.cssselect('a'):
                                getattr(vote, status)(cell.text.strip())

                    bill.add_vote(vote)
                    bill.add_source(vote_url)


    def scrape_bill(self, chamber, session, bill_type, number):
        """ Creates a bill object
        """
        if len(session) == 4:
            session_url = session+'rs'
        else:
            session_url = session
        url = BILL_URL % (session_url, bill_type, number)
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            # title
            # find <a name="Title">, get parent dt, get parent dl, then get dd within dl
            title = doc.cssselect('a[name=Title]')[0] \
                .getparent().getparent().cssselect('dd')[0].text.strip()

            # create the bill object now that we have the title
            print "%s %d %s" % (bill_type, number, title)
            bill = Bill(session, chamber, "%s %d" % (bill_type, number), title)
            bill.add_source(url)

            self.parse_bill_sponsors(doc, bill)     # sponsors
            self.parse_bill_actions(doc, bill)      # actions
            self.parse_bill_documents(doc, bill)    # documents and versions
            self.parse_bill_votes(doc, bill)        # votes

            # add bill to collection
            self.save_bill(bill)


    def scrape(self, chamber, session):

        self.validate_session(session)

        for bill_type in CHAMBERS[chamber]:
            for i in itertools.count(1):
                try:
                    self.scrape_bill(chamber, session, bill_type, i)
                except HTTPError, he:
                    if he.response.code != 404:
                        raise he
                    break
