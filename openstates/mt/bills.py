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

        self.vote_results = defaultdict(list)

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
            if bill:
                self.save_bill(bill)

    def parse_bill(self, bill_url, session, chamber):

        # Temporarily skip the differently-formatted house budget bill.
        if '/2011/billhtml/hb0002.htm' in bill_url.lower():
            return

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

    def _get_tabledata(self, status_page):
        '''Montana doesn't currently list co/multisponsors on any of the 
        legislation I've seen. So this function only adds the primary 
        sponsor.'''
        tabledata = defaultdict(list)
        join = ' '.join

        # Get the top data table.
        for tr in status_page.xpath('//tr'):
            tds = tr.xpath("td")
            try:
                key = tds[0].text_content().lower()
                val = join(tds[1].text_content().strip().split())
            except IndexError:
                continue
            if not key.startswith('('):
                tabledata[key].append(val)

        return dict(tabledata)

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
        self.add_actions(bill, status_page)
        self.add_votes(bill, status_page, status_url)

        tabledata = self._get_tabledata(status_page)

        # Add sponsor info.
        bill.add_sponsor('primary', tabledata['primary sponsor:'][0])

        # A various plus fields MT provides.
        plus_fields = [
            'requester',
            ('chapter number:', 'chapter'),
            'transmittal date:',
            'drafter',
            'fiscal note probable:',
            'bill draft number:',
            'preintroduction required:',
            'by request of',
            'category:']

        for x in plus_fields:
            if isinstance(x, tuple):
                _key, key = x
            else:
                _key = key = x
                key = key.replace(' ', '_')

            try:
                val = tabledata[_key]
            except KeyError:
                continue

            if len(val) == 1:
                val = val[0]

            bill[key] = val

        # Add bill subjects.
        xp = '//th[contains(., "Revenue/Approp.")]/ancestor::table/tr'
        subjects = []
        for tr in status_page.xpath(xp):
            try:
                subj = tr.xpath('td')[0].text_content()
            except:
                continue
            subjects.append(subj)

        bill['subjects'] = subjects

        if None in bill['votes'] or bill['votes'] is None:
            pdb.set_trace()
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

    def _versions_dict(self, year):
        '''Get a mapping of ('HB', '2') tuples to version urls.'''

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
                    action = text.next().strip()
                    chamber, action = action.split(' ', 1)
                    date = datetime.strptime(text.next(), '%m/%d/%Y')

                    chamber = actor_map[chamber]
                    vote = Vote(chamber, date, None, 
                                passed=None, yes_count=None, no_count=None, 
                                other_count=None, action=action)

                    # Add the url as a source.
                    vote_url = vote_url[0]
                    vote.add_source(vote_url)

                    # Can't parse the votes from pdf. Frowny face.
                    if vote_url.lower().endswith('pdf'):
                        continue

                    # Update the vote object with voters..    
                    vote = self._parse_votes(vote_url, vote)
                    if vote:
                        bill.add_vote(vote)
                    
    def _parse_votes(self, url, vote):
        '''Given a vote url and a vote object, extract the voters and 
        the vote counts from the vote page and update the vote object.
        '''

        keymap = {'Y': 'yes', 'N': 'no'}

        html = self.urlopen(url).decode('latin-1')
        doc = lxml.html.fromstring(html)

        # Yes, no, excused, absent.
        try:
            vals = doc.xpath('//table')[1].xpath('tr/td/text()')
        except IndexError:
            # Fie upon't! This was a bogus link and lacked actual 
            # vote data.
            return 

        y, n, e, a = map(int, vals)

        # Correct the other count...
        vote['other_count'] = e + a

        for text in doc.xpath('//table')[2].xpath('tr/td/text()'):
            if not text.strip(u'\xa0'):
                continue
            v, name = filter(None, text.split(u'\xa0'))
            getattr(vote, keymap.get(v, 'other'))(name)

        yes_votes = vote['yes_count'] = len(vote['yes_votes'])
        no_votes = vote['no_count'] = len(vote['no_votes'])
        vote['other_count'] = len(vote['other_votes'])
        action = vote['action']

        try:
            motion = doc.xpath('//br')[-1].tail.strip()
        except:
            # Some of them mysteriously have no motion listed.
            motion = action

        vote['motion'] = motion

        # Existing code to deterimine value of `passed`
        passed = None

        # some actions take a super majority, so we aren't just 
        # comparing the yeas and nays here.
        for i in vote_passage_indicators:
            if action.count(i):
                passed = True
        for i in vote_failure_indicators:
            if action.count(i) and passed == True:
                # a quick explanation:  originally an exception was
                # thrown if both passage and failure indicators were
                # present because I thought that would be a bug in my
                # lists.  Then I found 2007 HB 160.
                # Now passed = False if the nays outnumber the yays..
                # I won't automatically mark it as passed if the yays
                # ounumber the nays because I don't know what requires
                # a supermajority in MT.
                if no_votes >= yes_votes:
                    passed = False
                else:
                    raise Exception("passage and failure indicator"
                                    "both present at: %s" % url)
            if action.count(i) and passed == None:
                passed = False
        for i in vote_ambiguous_indicators:
            if action.count(i):
                passed = yes_votes > no_votes
        if passed is None:
            raise Exception("Unknown passage at: %s" % url)

        vote['passed'] = passed

        return vote