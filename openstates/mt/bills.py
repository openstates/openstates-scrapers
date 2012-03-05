import os
import re
import pdb
import itertools
import copy
from datetime import datetime
from urlparse import urljoin
from collections import defaultdict
from operator import getitem

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from scrapelib import urlopen

import lxml.html
from lxml.etree import ElementTree

def url2lxml(url):
    html = urlopen(url).decode('latin-1')
    return lxml.html.fromstring(html)


actor_map = {
    '(S)': 'upper',
    '(H)': 'lower',
    '(C)': 'clerk',
    }

sponsor_map = {
    'Primary Sponsor': 'primary'
    }

vote_passage_indicators = ['Adopted',
                           'Appointed',
                           'Carried',
                           'Concurred',
                           'Dissolved',
                           'Passed',
                           'Rereferred to Committee',
                           'Transmitted to',
                           'Veto Overidden',
                           'Veto Overridden']
vote_failure_indicators = ['Failed',
                           'Rejected',
                           ]
vote_ambiguous_indicators = [
    'Indefinitely Postponed',
    'On Motion Rules Suspended',
    'Pass Consideration',
    'Reconsidered Previous',
    'Rules Suspended',
    'Segregated from Committee',
    'Special Action',
    'Sponsor List Modified',
    'Tabled',
    'Taken from']

class MTBillScraper(BillScraper):
    #must set state attribute as the state's abbreviated name
    state = 'mt'

    def __init__(self, *args, **kwargs):
        super(MTBillScraper, self).__init__(*args, **kwargs)

        self.search_url_template = (
            'http://laws.leg.mt.gov/laws%s/LAW0203W$BSRV.ActionQuery?'
            'P_BLTP_BILL_TYP_CD=%s&P_BILL_NO=%s&P_BILL_DFT_NO=&'
            'Z_ACTION=Find&P_SBJ_DESCR=&P_SBJT_SBJ_CD=&P_LST_NM1=&'
            'P_ENTY_ID_SEQ=')

    def scrape(self, chamber, session):
        for term in self.metadata['terms']:
            if session in term['sessions']:
                year = term['start_year']
                break

        self.versions_dict = self._versions_dict(year)

        base_bill_url = 'http://data.opi.mt.gov/bills/%d/BillHtml/' % year
        index_page = ElementTree(lxml.html.fromstring(self.urlopen(base_bill_url)))

        bill_urls = []
        for bill_anchor in index_page.findall('//a'):
            # See 2009 HB 645
            if bill_anchor.text.find("govlineveto") == -1:
                # House bills start with H, Senate bills start with S
                if chamber == 'lower' and bill_anchor.text.startswith('H'):
                    bill_urls.append("%s%s" % (base_bill_url, bill_anchor.text))
                elif chamber == 'upper' and bill_anchor.text.startswith('S'):
                    bill_urls.append("%s%s" % (base_bill_url, bill_anchor.text))

        for bill_url in bill_urls:
            bill = self.parse_bill(bill_url, session, chamber)
            self.save_bill(bill)

    def parse_bill(self, bill_url, session, chamber):
        bill = None
        bill_page = ElementTree(lxml.html.fromstring(self.urlopen(bill_url)))
        
        for anchor in bill_page.findall('//a'):
            if (anchor.text_content().startswith('status of') or
                anchor.text_content().startswith('Detailed Information (status)')):
                status_url = anchor.attrib['href'].replace("\r", "").replace("\n", "")
                bill = self.parse_bill_status_page(status_url, bill_url, session, chamber)

        if bill is None:
            # No bill was found.  Maybe something like HB0790 in the 2005 session?
            # We can search for the bill metadata.
            page_name = bill_url.split("/")[-1].split(".")[0]
            bill_type = page_name[0:2]
            bill_number = page_name[2:]
            laws_year = self.metadata['session_details'][session]['years'][0] % 100

            status_url = self.search_url_template % (laws_year, bill_type, bill_number)
            bill = self.parse_bill_status_page(status_url, bill_url, session, chamber)

        # Get versions on the detail page.
        versions = [a['action'] for a in bill['actions']]
        versions = [a for a in versions if 'Version Available' in a]
        if not versions:
            version_name = 'Introduced'
        else:
            version = versions.pop()
            if 'New Version' in version:
                version_name = 'Amended'
            elif 'Enrolled' in version:
                version_name = 'Enrolled'

        self.add_other_versions(bill)

        # Add html.
        bill.add_version(version_name, bill_url, mimetype='text/html')

        # Add pdf.
        url = set(bill_page.xpath('//a/@href[contains(., "BillPdf")]')).pop()
        bill.add_version(version_name, url, mimetype='application/pdf')

        # Add status url as a source.
        bill.add_source(status_url)

        return bill

    def parse_bill_status_page(self, status_url, bill_url, session, chamber):
        status_page = lxml.html.fromstring(self.urlopen(status_url))
        # see 2007 HB 2... weird.
        try:
            bill_id = status_page.xpath("//tr[2]/td[2]")[0].text_content()
        except IndexError:
            bill_id = status_page.xpath('//tr[1]/td[2]')[0].text_content()

        try:
            title = status_page.xpath("//form[1]/table[2]/tr[3]/td[2]")[0].text_content()
        except IndexError:
            title = status_page.xpath('//tr[1]/td[2]')[0].text_content()

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(bill_url)

        self.add_sponsors(bill, status_page)
        self.add_actions(bill, status_page)
        self.add_votes(bill, status_page, status_url)

        return bill


    def add_actions(self, bill, status_page):
        
        for action in reversed(status_page.xpath('//div/form[3]/table[1]/tr')[1:]):
            try:
                actor = actor_map[action.xpath("td[1]")[0].text_content().split(" ")[0]]
                action_name = action.xpath("td[1]")[0].text_content().replace(actor, "")[4:].strip()
            except KeyError:
                action_name = action.xpath("td[1]")[0].text_content().strip()
                actor = 'clerk' if action_name == 'Chapter Number Assigned' else ''

            action_name = action_name.replace("&nbsp", "")
            action_date = datetime.strptime(action.xpath("td[2]")[0].text, '%m/%d/%Y')
            action_votes_yes = action.xpath("td[3]")[0].text_content().replace("&nbsp", "")
            action_votes_no = action.xpath("td[4]")[0].text_content().replace("&nbsp", "")
            action_committee = action.xpath("td[5]")[0].text.replace("&nbsp", "")

            bill.add_action(actor, action_name, action_date)

            # TODO: Review... should something be both an action and a vote?            
            try:
                action_votes_yes = int(action_votes_yes)
                action_votes_no = int(action_votes_no)
            except ValueError:
                continue

            passed = None

            # some actions take a super majority, so we aren't just 
            # comparing the yeas and nays here.
            for i in vote_passage_indicators:
                if action_name.count(i):
                    passed = True
            for i in vote_failure_indicators:
                if action_name.count(i) and passed == True:
                    # a quick explanation:  originally an exception was
                    # thrown if both passage and failure indicators were
                    # present because I thought that would be a bug in my
                    # lists.  Then I found 2007 HB 160.
                    # Now passed = False if the nays outnumber the yays..
                    # I won't automatically mark it as passed if the yays
                    # ounumber the nays because I don't know what requires
                    # a supermajority in MT.
                    if action_votes_no >= action_votes_yes:
                        passed = False
                    else:
                        raise Exception ("passage and failure indicator"
                                         "both present: %s" % action_name)
                if action_name.count(i) and passed == None:
                    passed = False
            for i in vote_ambiguous_indicators:
                if action_name.count(i):
                    passed = action_votes_yes > action_votes_no
            if passed is None:
                raise Exception("Unknown passage: %s" % action_name)
            bill.add_vote(Vote(bill['chamber'],
                               action_date,
                               action_name,
                               passed,
                               action_votes_yes,
                               action_votes_no,
                               0))

    def add_sponsors(self, bill, status_page):
        for sponsor_row in status_page.xpath('/div/form[6]/table[1]/tr')[1:]:
            sponsor_type = sponsor_row.xpath("td[1]")[0].text
            sponsor_last_name = sponsor_row.xpath("td[2]")[0].text
            sponsor_first_name = sponsor_row.xpath("td[3]")[0].text
            sponsor_middle_initial = sponsor_row.xpath("td[4]")[0].text

            sponsor_middle_initial = sponsor_middle_initial.replace("&nbsp", "")
            sponsor_full_name = "%s, %s %s" % (sponsor_last_name,  sponsor_first_name, sponsor_middle_initial)
            sponsor_full_name = sponsor_full_name.strip()

            if sponsor_map.has_key(sponsor_type):
                sponsor_type = sponsor_map[sponsor_type]
            bill.add_sponsor(sponsor_type, sponsor_full_name)

    def _versions_dict(self, year):

        res = defaultdict(dict)

        url = 'http://data.opi.mt.gov/bills/%d/' % year
        doc = url2lxml(url)
        for url in doc.xpath('//a[contains(@href, "/bills/")]/@href')[1:]:
            doc = url2lxml(url)
            for fn in doc.xpath('//a/@href')[1:]:
                _url = urljoin(url, fn)
                _, _, fn = fn.rpartition('/')
                m = re.search(r'([A-Z]+)0*(\d+)_?([^.]+)', fn)
                if m:
                    type_, id_, version = m.groups()
                    res[(type_, id_)][version] = _url

        return res

    def add_other_versions(self, bill):

        count = itertools.count(1)
        xcount = itertools.chain([1], itertools.count(1))
        type_, id_ = bill['bill_id'].split()        
        version_urls = copy.copy(self.versions_dict[(type_, id_)])
        mimetype = 'application/pdf'
        version_strings = [
            'Introduced Bill Text Available Electronically',
            'Printed - New Version Available',
            'Clerical Corrections Made - New Version Available']

        if bill['bill_id'] == 'HB 2':
            # Need to special-case this one.
            return

        for i, a in enumerate(bill['actions']):
            
            text = a['action']
            actions = bill['actions']
            if text in version_strings:

                name = actions[i - 1]['action']

                if 'Clerical Corrections' in text:
                    name += ' (clerical corrections made)'
                try:
                    url = version_urls.pop(str(count.next()))    
                except KeyError:
                    msg = "No url found for version: %r" % name
                    self.warning(msg)
                else:
                    bill.add_version(name, url, mimetype)
                    continue

                try:
                    url = version_urls['x' + str(xcount.next())]
                except KeyError:
                    continue

                name = actions[i - 1]['action']
                bill.add_version(name, url, mimetype)

    def add_votes(self, bill, status_page, status_url):
        '''For each row in the actions table that links to a vote,
        retrieve the vote object created by the scraper in add_actions
        and update the vote object with the voter data.
        '''
        base_url, _, _ = status_url.rpartition('/')
        base_url += '/'
        status_page.make_links_absolute(base_url)

        if not bill['votes']:
            return 

        votes = {}    
        for vote in bill['votes']:
            votes[(vote['motion'], vote['date'])] = vote

        for tr in status_page.xpath('//table')[4].xpath('tr')[2:]:
            tds = list(tr)

            if tds:
                vote_url = tds[2].xpath('a/@href')

                if vote_url:

                    # Get the matching vote object.
                    text = tr.itertext()
                    motion = text.next().strip()
                    _, motion = motion.split(' ', 1)
                    date = datetime.strptime(text.next(), '%m/%d/%Y')
                    vote = votes[(motion, date)]

                    # Add the url as a source.
                    vote_url = vote_url[0]
                    vote.add_source(vote_url)

                    # Can't parse the votes from pdf. Frowny face.
                    if vote_url.lower().endswith('pdf'):
                        continue

                    # Update the vote object with voters..    
                    data = self._parse_votes(vote_url, vote)
                    
    def _parse_votes(self, url, vote):
        '''Given a vote url and a vote object, extract the voters and 
        the vote counts from the vote page and update the vote object.
        '''

        keymap = {'Y': 'yes',
                  'N': 'no'}

        html = self.urlopen(url).decode('latin-1')
        doc = lxml.html.fromstring(html)

        # Yes, no, excused, absent.
        try:
            vals = doc.xpath('//table')[1].xpath('tr/td/text()')
        except IndexError:
            # Fie upon't! This was a bogus link and lacked actual vote data.
            return 

        y, n, e, a = map(int, vals)

        # Correct the other count...
        vote['other_count'] = e + a

        for text in doc.xpath('//table')[2].xpath('tr/td/text()'):
            if not text.strip(u'\xa0'):
                continue
            v, name = filter(None, text.split(u'\xa0'))
            getattr(vote, keymap.get(v, 'other'))(name)

