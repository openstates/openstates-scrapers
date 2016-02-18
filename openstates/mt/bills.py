import os
import re
import itertools
import copy
import tempfile
from datetime import datetime
from urlparse import urljoin
from collections import defaultdict

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf
from scrapelib import HTTPError

import lxml.html
from lxml.etree import ElementTree, XMLSyntaxError

from openstates.utils import LXMLMixin
from . import actions


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


class MTBillScraper(BillScraper, LXMLMixin):
    #must set state attribute as the state's abbreviated name
    jurisdiction = 'mt'

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

        base_bill_url = 'http://leg.mt.gov/bills/%d/BillHtml/' % year
        index_page = ElementTree(lxml.html.fromstring(self.get(base_bill_url).text))

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
        if 'billhtml/hb0002.htm' in bill_url.lower():
            return

        bill = None
        try:
            doc = lxml.html.fromstring(self.get(bill_url).text)
        except XMLSyntaxError as e:
            self.logger.warning("Got %r while parsing %r" % (e, bill_url))
            return
        bill_page = ElementTree(doc)

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
            tds = tr.xpath('td')
            try:
                key = tds[0].text_content().lower()
                if (key == 'primary sponsor:'):
                    val = re.sub(r'[\s]+', ' ', tds[1].xpath('./a/text()')[0])
                else:
                    val = join(tds[1].text_content().strip().split())
            except IndexError:
                continue
            if not key.startswith('('):
                tabledata[key].append(val)

        return dict(tabledata)

    def parse_bill_status_page(self, status_url, bill_url, session, chamber):
        status_page = lxml.html.fromstring(self.get(status_url).text)
        # see 2007 HB 2... weird.
        bill_re = r'.*?/([A-Z]+)0*(\d+)\.pdf'
        bill_xpath = '//a[contains(@href, ".pdf") and ' + \
                'contains(@href, "billpdf")]/@href'
        bill_id = re.search(bill_re, status_page.xpath(bill_xpath)[0],
                re.IGNORECASE).groups()
        bill_id = "{0} {1}".format(bill_id[0], int(bill_id[1]))

        try:
            xp = '//b[text()="Short Title:"]/../following-sibling::td/text()'
            title = status_page.xpath(xp).pop()
        except IndexError:
            title = status_page.xpath('//tr[1]/td[2]')[0].text_content()

        # Add bill type.
        _bill_id = bill_id.lower()
        if 'b' in _bill_id:
            type_ = 'bill'

        elif 'j' in _bill_id or 'jr' in _bill_id:
            type_ = 'joint resolution'

        elif 'cr' in _bill_id:
            type_ = 'concurrent resolution'

        elif 'r' in _bill_id:
            type_ = 'resolution'

        bill = Bill(session, chamber, bill_id, title, type=type_)
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

        self.add_fiscal_notes(status_page, bill)

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
            action_type = actions.categorize(action_name)

            if 'by senate' in action_name.lower():
                actor = 'upper`'
            bill.add_action(actor, action_name, action_date, action_type)

    def _versions_dict(self, year):
        '''Get a mapping of ('HB', '2') tuples to version urls.'''

        res = defaultdict(dict)

        url = 'http://leg.mt.gov/bills/%d/' % year

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        for url in doc.xpath('//a[contains(@href, "/bills/")]/@href')[1:]:
            doc = self.lxmlize(url)
            for fn in doc.xpath('//a/@href')[1:]:
                _url = urljoin(url, fn)
                fn = fn.split('/')[-1]
                m = re.search(r'([A-Z]+)0*(\d+)_?(.*?)\.pdf', fn)
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
                    if 'Introduced Bill' in text:
                        name = 'Introduced'
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

        for tr in status_page.xpath('//table')[3].xpath('tr')[2:]:
            tds = list(tr)

            if tds:
                vote_url = tds[2].xpath('a/@href')

                if vote_url:

                    # Get the matching vote object.
                    text = tr.itertext()
                    action = text.next().strip()
                    chamber, action = action.split(' ', 1)
                    date = datetime.strptime(text.next(), '%m/%d/%Y')
                    vote_url = vote_url[0]

                    chamber = actor_map[chamber]
                    vote = dict(chamber=chamber, date=date,
                                action=action,
                                sources=[{'url': vote_url}])

                    # Update the vote object with voters..
                    vote = self._parse_votes(vote_url, vote)
                    if vote:
                        bill.add_vote(vote)

    def _parse_votes(self, url, vote):
        '''Given a vote url and a vote object, extract the voters and
        the vote counts from the vote page and update the vote object.
        '''
        if url.lower().endswith('.pdf'):

            try:
                resp = self.get(url)
            except HTTPError:
                # This vote document wasn't found.
                msg = 'No document found at url %r' % url
                self.logger.warning(msg)
                return

            try:
                v = PDFCommitteeVote(url, resp.content)
                return v.asvote()
            except PDFCommitteeVoteParseError as e:
                # Warn and skip.
                self.warning("Could't parse committee vote at %r" % url)
                return

        keymap = {'Y': 'yes', 'N': 'no'}
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        # Yes, no, excused, absent.
        try:
            vals = doc.xpath('//table')[1].xpath('tr/td/text()')
        except IndexError:
            # Most likely was a bogus link lacking vote data.
            return

        y, n, e, a = map(int, vals)
        vote.update(yes_count=y, no_count=n, other_count=e + a)

        # Get the motion.
        try:
            motion = doc.xpath('//br')[-1].tail.strip()
        except:
            # Some of them mysteriously have no motion listed.
            motion = vote['action']

        if not motion:
            motion = vote['action']

        vote['motion'] = motion

        # Add placeholder for passed (see below)
        vote['passed'] = False

        vote = Vote(**vote)

        for text in doc.xpath('//table')[2].xpath('tr/td/text()'):
            if not text.strip(u'\xa0'):
                continue
            v, name = filter(None, text.split(u'\xa0'))
            getattr(vote, keymap.get(v, 'other'))(name)

        action = vote['action']

        # Existing code to deterimine value of `passed`
        yes_votes = vote['yes_votes']
        no_votes = vote['no_votes']
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

    def add_fiscal_notes(self, doc, bill):

        for link in doc.xpath('//a[contains(text(), "Fiscal Note")]'):
            bill.add_document(name=link.text_content().strip(),
                              url=link.attrib['href'],
                              mimetype='application/pdf')


class PDFCommitteeVoteParseError(Exception):
    pass


class PDFCommitteeVote404Error(PDFCommitteeVoteParseError):
    pass


class PDFCommitteeVote(object):

    def __init__(self, url, resp):

        self.url = url

        # Fetch the document and put it into tempfile.
        fd, filename = tempfile.mkstemp()

        with open(filename, 'wb') as f:
            f.write(resp)

        # Convert it to text.
        try:
            text = convert_pdf(filename, type='text')
        except:
            msg = "couldn't convert pdf."
            raise PDFCommitteeVoteParseError(msg)

        # Get rid of the temp file.
        os.close(fd)
        os.remove(filename)

        if not text.strip():
            msg = 'PDF file was empty.'
            raise PDFCommitteeVoteParseError(msg)

        self.text = '\n'.join(filter(None, text.splitlines()))

    def committee(self):
        """
        XXX: OK. So, the error here:


            When we have a `joint' chamber vote, we also need the committee
            attached with the bill, or the OCD conversion won't know which
            committee on the whole to associate with.

            In addition, matching to the COW is wrong; since this was a
            committee vote. I'm stubbing this out since the site is currently
            offline
        """
        raise NotImplemented

    def chamber(self):
        chamber_dict = {'HOUSE': 'lower', 'SENATE': 'upper', 'JOINT': 'joint'}
        chamber = re.search(r'(HOUSE|SENATE|JOINT)', self.text)
        if chamber is None:
            raise PDFCommitteeVoteParseError("PDF didn't have chamber on it")
        return chamber_dict[chamber.group(1)]

    def date(self):

        months = '''january february march april may june july
            august september october november december'''.split()

        text = iter(self.text.splitlines())

        line = text.next().strip()
        while True:

            _line = line.lower()
            break_outer = False
            for m in months:
                if m in _line:
                    break_outer = True
                    break

            if break_outer:
                break

            try:
                line = text.next().strip()
            except StopIteration:
                msg = 'Couldn\'t parse the vote date.'
                raise PDFCommitteeVoteParseError(msg)

        try:
            return datetime.strptime(line, '%B %d, %Y')
        except ValueError:
            raise PDFCommitteeVoteParseError("Could't parse the vote date.")

    def motion(self):

        text = iter(self.text.splitlines())

        while True:
            line = text.next()
            if 'VOTE TABULATION' in line:
                break

        line = text.next()
        _, motion = line.split(' - ')
        motion = motion.strip()
        return motion

    def _getcounts(self):
        m = re.search(r'YEAS \- .+$', self.text, re.MULTILINE)
        if m:
            x = m.group()
        else:
            msg = "Couldn't find vote counts."
            raise PDFCommitteeVoteParseError(msg)
        self._counts_data = dict(re.findall(r'(\w+) - (\d+)', x))

    def yes_count(self):
        if not hasattr(self, '_counts_data'):
            self._getcounts()
        return int(self._counts_data['YEAS'])

    def no_count(self):
        if not hasattr(self, '_counts_data'):
            self._getcounts()
        return int(self._counts_data['NAYS'])

    def other_count(self):
        return len(self.other_votes())

    def _getvotes(self):
        junk = ['; by Proxy']
        res = defaultdict(list)
        data = re.findall(r'([A-Z]) {6,7}(.+)', self.text, re.MULTILINE)
        for val, name in data:
            for j in junk:
                name = name.replace(j, '')
            res[val].append(name)
        self._votes_data = res

    def yes_votes(self):
        if not hasattr(self, '_votes_data'):
            self._getvotes()
        return self._votes_data['Y']

    def other_votes(self):
        if not hasattr(self, '_votes_data'):
            self._getvotes()
        return self._votes_data['--']

    def no_votes(self):
        if not hasattr(self, '_votes_data'):
            self._getvotes()
        return self._votes_data['N']

    def passed(self):
        return self.no_count() < self.yes_count()

    def asdict(self):
        res = {}
        methods = ('yes_count', 'no_count', 'motion', 'chamber',
                   'other_count', 'passed', 'date')
        # TODO: re-add committee
        for m in methods:
            res[m] = getattr(self, m)()
        return res

    def asvote(self):
        v = Vote(**self.asdict())
        for key in 'yes_votes no_votes other_votes'.split():
            v[key] = getattr(self, key)()
        v.add_source(self.url)
        return v
