#!/usr/bin/env python
import datetime
import itertools
import os
import re
import sys
import time
from urllib2 import HTTPError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 Committee, NoDataForYear)

CHAMBERS = {
    'upper': ('SB','SJ'),
    'lower': ('HB','HJ'),
}
SESSIONS = {
    '2010': ('rs',),
    '2009': ('rs',),
    '2008': ('rs',),
    '2007': ('rs','s1'),
    '2006': ('rs','s1'),
    '2005': ('rs',),
    '2004': ('rs','s1'),
    '2003': ('rs',),
    '2002': ('rs',),
    '2001': ('rs',),
    '2000': ('rs',),
    '1999': ('rs',),
    '1998': ('rs',),
    '1997': ('rs',),
    '1996': ('rs',),
}

BASE_URL = "http://mlis.state.md.us"
BILL_URL = BASE_URL + "/%s%s/billfile/%s%04d.htm" # year, session, bill_type, number

MOTION_RE = re.compile(r"(?P<motion>[\w\s]+) \((?P<yeas>\d{1,3})-(?P<nays>\d{1,3})\)")

class MDLegislationScraper(LegislationScraper):

    state = 'md'

    metadata = {
        'state_name': 'Maryland',
        'legislature_name': 'Maryland General Assembly',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Delegates',
        'upper_title': 'Senator',
        'lower_title': 'Delegate',
        'upper_term': 4,
        'lower_term': 4,
        'sessions': SESSIONS.keys(),
        'session_details': {
            '2007-2008': {'years': [2007, 2008], 'sub_sessions':
                              ['Sub Session 1', 'Sub Session 2']},
            '2009-2010': {'years': [2009, 2010], 'sub_sessions': []}}}

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
        for h5 in doc.cssselect('h5'):
            if h5.text in ('House Action', 'Senate Action'):
                chamber = 'upper' if h5.text == 'Senate Action' else 'lower'
                elems = h5.getnext().cssselect('dt')
                for elem in elems:
                    action_date = elem.text.strip()
                    if action_date != "No Action":
                        try:
                            action_date = datetime.datetime.strptime(
                                "%s/%s" % (action_date, bill['session']), '%m/%d/%Y')
                            action_desc = ""
                            dd_elem = elem.getnext()
                            while dd_elem is not None and dd_elem.tag == 'dd':
                                if action_desc:
                                    action_desc = "%s %s" % (action_desc, dd_elem.text.strip())
                                else:
                                    action_desc = dd_elem.text.strip()
                                dd_elem = dd_elem.getnext()
                            bill.add_action(chamber, action_desc, action_date)
                        except ValueError:
                            pass # probably trying to parse a bad entry, not really an action

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
                with self.lxml_context(vote_url) as vote_doc:
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


    def scrape_bill(self, chamber, year, session, bill_type, number):
        """ Creates a bill object
        """
        url = BILL_URL % (year, session, bill_type, number)
        with self.lxml_context(url) as doc:
            # title
            # find <a name="Title">, get parent dt, get parent dl, then get dd within dl
            title = doc.cssselect('a[name=Title]')[0] \
                .getparent().getparent().cssselect('dd')[0].text.strip()

            # create the bill object now that we have the title
            print "%s %d %s" % (bill_type, number, title)
            bill = Bill(year, chamber, "%s %d" % (bill_type, number), title)
            bill.add_source(url)

            self.parse_bill_sponsors(doc, bill)     # sponsors
            self.parse_bill_actions(doc, bill)      # actions
            self.parse_bill_documents(doc, bill)    # documents and versions
            self.parse_bill_votes(doc, bill)        # votes

            # add bill to collection
            self.save_bill(bill)


    def scrape_session(self, chamber, year, session):
        for bill_type in CHAMBERS[chamber]:
            for i in itertools.count(1):
                try:
                    self.scrape_bill(chamber, year, session, bill_type, i)
                except HTTPError, he:
                    # hope this is because the page doesn't exist
                    # and not because something is broken
                    if he.code != 404:
                        raise he
                    break

    def scrape_bills(self, chamber, year):

        if year not in SESSIONS:
            raise NoDataForYear(year)

        for session in SESSIONS[year]:
            self.scrape_session(chamber, year, session)


    def scrape_members(self, url, chamber):
        detail_re = re.compile('\((R|D)\), (?:Senate President, )?(?:House Speaker, )?District (\w+)')

        with self.lxml_context(url) as doc:
            # data on this page is <li>s that have anchor tags
            for a in doc.cssselect('li a'):
                link = a.get('href')
                # tags don't close so we get the <li> and <a> content and diff them
                name_text = a.text_content()
                detail_text = a.getparent().text_content().replace(name_text, '')

                # ignore if it is not a valid link
                if link:
                    # handle names
                    names = name_text.split(',')
                    last_name = names[0]
                    first_name = names[1]
                    # TODO: try to trim first name to remove middle initial
                    if len(names) > 2:
                        suffix = names[2]
                    else:
                        suffix = None

                    # handle details
                    details = detail_text.strip()
                    party, district = detail_re.match(details).groups()

                    leg = Legislator('current', chamber, district,
                                     ' '.join((first_name, last_name)),
                                     first_name, last_name, '',
                                     party, suffix=suffix,
                                     url='http://www.msa.md.gov'+link)
                    self.save_legislator(leg)


    def scrape_legislators(self, chamber, year):
        house_url = 'http://www.msa.md.gov/msa/mdmanual/06hse/html/hseal.html'
        sen_url = "http://www.msa.md.gov/msa/mdmanual/05sen/html/senal.html"

        if year not in SESSIONS:
            raise NoDataForYear(year)

        self.scrape_members(house_url, 'lower')
        self.scrape_members(sen_url, 'upper')


    def scrape_committees(self, chamber, year):
        house_url = 'http://www.msa.md.gov/msa/mdmanual/06hse/html/hsecom.html'
        with self.lxml_context(house_url) as doc:
            # distinct URLs containing /com/
            committees = set([l.get('href') for l in doc.cssselect('li a')
                              if l.get('href', '').find('/com/') != -1])

        for com in committees:
            com_url = 'http://www.msa.md.gov'+com
            with self.lxml_context(com_url) as cdoc:
                for h in cdoc.cssselect('h2, h3'):
                    if h.text:
                        committee_name = h.text
                        break
                cur_com = Committee('lower', committee_name)
                cur_com.add_source(com_url)
                for l in cdoc.cssselect('a[href]'):
                    if ' SUBCOMMITTEE' in (l.text or ''):
                        self.save_committee(cur_com)
                        cur_com = Committee('lower', l.text, committee_name)
                        cur_com.add_source(com_url)
                    elif 'html/msa' in l.get('href'):
                        cur_com.add_member(l.text)
                self.save_committee(cur_com)
