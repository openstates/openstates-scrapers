# -*- coding: utf-8 -*-
import re
import os
from collections import defaultdict
import datetime
from urllib import urlencode
import scrapelib

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf
from openstates.utils import LXMLMixin


def group(lst, n):
    # from http://code.activestate.com/recipes/303060-group-a-list-into-sequential-n-tuples/
    for i in range(0, len(lst), n):
        val = lst[i:i+n]
        if len(val) == n:
            yield tuple(val)


TITLE_REMOVING_PATTERN = re.compile(".*(Rep|Sen). (.+)$")

SPONSOR_REFINE_PATTERN = re.compile(r'^Added (?P<spontype>.+) (?P<title>Rep|Sen)\. (?P<name>.+)')
SPONSOR_TYPE_REFINEMENTS = {
    'Chief Co-Sponsor': 'cosponsor',
    'as Chief Co-Sponsor': 'cosponsor',
    'Alternate Chief Co-Sponsor': 'cosponsor',
    'as Alternate Chief Co-Sponsor': 'cosponsor',
    'as Co-Sponsor': 'cosponsor',
    'Alternate Co-Sponsor':  'cosponsor',
    'as Alternate Co-Sponsor':  'cosponsor',
    'Co-Sponsor': 'cosponsor',
}


VERSION_TYPES = ('Introduced', 'Engrossed', 'Enrolled', 'Re-Enrolled')
FULLTEXT_DOCUMENT_TYPES = ('Public Act', "Governor's Message", )
# not as common, but maybe should just be added to FULLTEXT_DOCUMENT_TYPES?
# Amendatory Veto Motion \d{3}
# Conference Committee Report \d{3}

DOC_TYPES = {
    'B': 'bill',
    'R': 'resolution',
    'JR': 'joint resolution',
    'JRCA': 'constitutional amendment',
}

_action_classifiers = ( # see http://openstates.org/categorization/
    (re.compile(r'Amendment No. \d+ Filed'), 'amendment:introduced'),
    (re.compile(r'Amendment No. \d+ Tabled'), 'amendment:failed'),
    (re.compile(r'Amendment No. \d+ Adopted'), 'amendment:passed'),
    (re.compile(r'(Pref|F)iled with'), 'bill:filed'),
    (re.compile(r'Arrived? in'), 'bill:introduced'),
    (re.compile(r'First Reading'), 'bill:reading:1'),
    (re.compile(r'(Recalled to )?Second Reading'), 'bill:reading:2'),
    (re.compile(r'(Re-r|R)eferred to'), 'committee:referred'),
    (re.compile(r'(Re-a|A)ssigned to'), 'committee:referred'),
    (re.compile(r'Sent to the Governor'), 'governor:received'),
    (re.compile(r'Governor Approved'), 'governor:signed'),
    (re.compile(r'Governor Vetoed'), 'governor:vetoed'),
    (re.compile(r'Governor Item'), 'governor:vetoed:line-item'),
    (re.compile(r'Governor Amendatory Veto'), 'governor:vetoed'),
    (re.compile(r'Do Pass'), 'committee:passed'),
    (re.compile(r'Recommends Be Adopted'), 'committee:passed:favorable'),
    (re.compile(r'Be Adopted'), 'committee:passed:favorable'),
    (re.compile(r'Third Reading .+? Passed'), ['bill:reading:3', 'bill:passed']),
    (re.compile(r'Third Reading .+? Lost'), ['bill:reading:3', 'bill:failed']),
    (re.compile(r'Third Reading'), 'bill:reading:3'),
    (re.compile(r'Resolution Adopted'), 'bill:passed'),
    (re.compile(r'Resolution Lost'), 'bill:failed'),
    (re.compile(r'Session Sine Die',), 'bill:failed'),
    (re.compile(r'Tabled'), 'bill:withdrawn'),
)

OTHER_FREQUENT_ACTION_PATTERNS_WHICH_ARE_CURRENTLY_UNCLASSIFIED = [
    r'Accept Amendatory Veto - (House|Senate) (Passed|Lost) \d+-\d+\d+.?',
    r'Amendatory Veto Motion - (.+)',
    r'Balanced Budget Note (.+)',
    r'Effective Date(\s+.+ \d{4})?(;.+)?',
    r'To .*Subcommittee',
    r'Note Requested',
    r'Note Filed',
    r'^Public Act',
    r'Appeal Ruling of Chair',
    r'Added .*Sponsor',
    r'Remove(d)? .*Sponsor',
    r'Sponsor Removed',
    r'Sponsor Changed',
    r'^Chief .*Sponsor',
    r'^Co-Sponsor',
    r'Deadline Extended.+9\(b\)',
    r'Amendment.+Approved for Consideration',
    r'Approved for Consideration',
    r'Amendment.+Do Adopt',
    r'Amendment.+Concurs',
    r'Amendment.+Lost',
    r'Amendment.+Withdrawn',
    r'Amendment.+Motion.+Concur',
    r'Amendment.+Motion.+Table',
    r'Amendment.+Rules Refers',
    r'Amendment.+Motion to Concur Recommends be Adopted',
    r'Amendment.+Assignments Refers',
    r'Amendment.+Assignments Refers',
    r'Amendment.+Held',
    r'Motion.+Suspend Rule 25',
    r'Motion.+Reconsider Vote',
    r'Placed on Calendar',
    r'Amendment.+Postponed - (?P<committee>.+)',
    r'Postponed - (?P<committee>.+)',
    r"Secretary's Desk",
    r'Rule 2-10 Committee Deadline Established',
    r'^Held in (?P<committee>.+)'
]

VOTE_VALUES = ['NV', 'Y', 'N', 'E', 'A', 'P', '-']


def _categorize_action(action):
    for pattern, atype in _action_classifiers:
        if pattern.findall(action):
            kwargs = {"type": atype}
            if "committee:referred" in atype:
                kwargs['committees'] = [pattern.sub("", action).strip()]
            return kwargs
    return {"type": 'other'}

LEGISLATION_URL = ('http://ilga.gov/legislation/grplist.asp')


def build_url_for_legislation_list(metadata, chamber, session, doc_type):
    params = metadata['session_details'][session].get('params', {})
    params['num1'] = '1'
    params['num2'] = '10000'
    params['DocTypeID'] = doc_type
    return '?'.join([LEGISLATION_URL, urlencode(params)])


def chamber_slug(chamber):
    if chamber == 'lower':
        return 'H'
    return 'S'


class ILBillScraper(BillScraper, LXMLMixin):

    jurisdiction = 'il'

    def get_bill_urls(self, chamber, session, doc_type):
        url = build_url_for_legislation_list(self.metadata, chamber, session,
                                             doc_type)
        doc = self.lxmlize(url)
        for bill_url in doc.xpath('//li/a/@href'):
            yield bill_url

    def scrape(self, chamber, session):
        for doc_type in DOC_TYPES:
            doc_type = chamber_slug(chamber)+doc_type
            for bill_url in self.get_bill_urls(chamber, session, doc_type):
                self.scrape_bill(chamber, session, doc_type, bill_url)
        if chamber == 'upper':
            # add appointments and JSRs as upper chamber, not perfectly
            # accurate but it'll do
            for bill_url in self.get_bill_urls(chamber, session, 'AM'):
                self.scrape_bill(chamber, session, 'AM', bill_url,
                                 'appointment')
            for bill_url in self.get_bill_urls(chamber, session, 'JSR'):
                self.scrape_bill(chamber, session, 'JSR', bill_url,
                                 'joint session resolution')
            # TODO: also add EO's - they aren't voted upon anyway & we don't
            # handle governor so they are omitted for now

    def scrape_bill(self, chamber, session, doc_type, url, bill_type=None):
        try:
            doc = self.lxmlize(url)
        except scrapelib.HTTPError as e:
            assert '500' in e.args[0], "Unexpected error when accessing page: {}".format(e)
            self.warning("500 error for bill page; skipping bill")
            return

        # bill id, title, summary
        bill_num = re.findall('DocNum=(\d+)', url)[0]
        bill_type = bill_type or DOC_TYPES[doc_type[1:]]
        bill_id = doc_type + bill_num

        title = doc.xpath('//span[text()="Short Description:"]/following-sibling::span[1]/text()')[0].strip()
        summary = doc.xpath('//span[text()="Synopsis As Introduced"]/following-sibling::span[1]/text()')[0].strip()

        bill = Bill(session, chamber, bill_id, title, type=bill_type,
                    summary=summary)

        bill.add_source(url)
        # sponsors
        sponsor_list = build_sponsor_list(doc.xpath('//a[@class="content"]'))
        # don't add just yet; we can make them better using action data

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
                            **_categorize_action(action))
            if action.lower().find('sponsor') != -1:
                self.refine_sponsor_list(actor, action, sponsor_list, bill_id)

        # now add sponsors
        for spontype, sponsor, chamber, official_type in sponsor_list:
            if chamber:
                bill.add_sponsor(spontype, sponsor,
                                 official_type=official_type, chamber=chamber)
            else:
                bill.add_sponsor(spontype, sponsor,
                                 official_type=official_type)

        # versions
        version_url = doc.xpath('//a[text()="Full Text"]/@href')[0]
        self.scrape_documents(bill, version_url)

        # if there's more than 1 votehistory link, there are votes to grab
        if len(doc.xpath('//a[contains(@href, "votehistory")]')) > 1:
            votes_url = doc.xpath('//a[text()="Votes"]/@href')[0]
            self.scrape_votes(session, bill, votes_url)

        self.save_bill(bill)

    def scrape_documents(self, bill, version_url):
        doc = self.lxmlize(version_url)

        for link in doc.xpath('//a[contains(@href, "fulltext")]'):
            name = link.text
            url = link.get('href')
            if name in VERSION_TYPES:
                bill.add_version(name, url + '&print=true',
                                 mimetype='text/html')
            elif 'Amendment' in name or name in FULLTEXT_DOCUMENT_TYPES:
                bill.add_document(name, url)
            elif 'Printer-Friendly' in name:
                pass
            else:
                self.warning('unknown document type %s - adding as document' % name)
                bill.add_document(name, url)

    def scrape_votes(self, session, bill, votes_url):
        doc = self.lxmlize(votes_url)

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

            for date_format in ["%b %d, %Y", "%A, %B %d, %Y"]:
                try:
                    date = datetime.datetime.strptime(date, date_format)
                    break
                except ValueError:
                    continue
            else:
                raise AssertionError(
                        "Date '{}' does not follow a format".format(date))

            vote = self.scrape_pdf_for_votes(session, chamber, date, motion.strip(), link.get('href'))

            bill.add_vote(vote)

        bill.add_source(votes_url)

    def fetch_pdf_lines(self, href):
        # download the file
        fname, resp = self.urlretrieve(href)
        pdflines = [line.decode('utf-8') for line in convert_pdf(fname, 'text').splitlines()]
        os.remove(fname)
        return pdflines

    def scrape_pdf_for_votes(self, session, chamber, date, motion, href):
        warned = False
        # vote indicator, a few spaces, a name, newline or multiple spaces
        VOTE_RE = re.compile('(Y|N|E|NV|A|P|-)\s{2,5}(\w.+?)(?:\n|\s{2})')
        COUNT_RE = re.compile(r'^(\d+)\s+YEAS?\s+(\d+)\s+NAYS?\s+(\d+)\s+PRESENT(?:\s+(\d+)\s+NOT\sVOTING)?\s*$')
        PASS_FAIL_WORDS = {
            'PASSED': True,
            'PREVAILED': True,
            'ADOPTED': True,
            'CONCURRED': True,
            'FAILED': False,
            'LOST': False,
        }

        pdflines = self.fetch_pdf_lines(href)

        yes_count = no_count = present_count = other_count = 0
        yes_votes = []
        no_votes = []
        present_votes = []
        other_vote_detail = defaultdict(list)
        passed = None
        counts_found = False
        vote_lines = []
        for line in pdflines:
            # consider pass/fail as a document property instead of a result of the vote count
            # extract the vote count from the document instead of just using counts of names
            if not line.strip():
                continue
            elif line.strip() in PASS_FAIL_WORDS:
                if passed is not None:
                    raise Exception("Duplicate pass/fail matches in [%s]" % href)
                passed = PASS_FAIL_WORDS[line.strip()]
            elif COUNT_RE.match(line):
                yes_count, no_count, present_count, not_voting_count = COUNT_RE.match(line).groups()
                yes_count = int(yes_count)
                no_count = int(no_count)
                present_count = int(present_count)
                counts_found = True
            elif counts_found:
                for value in VOTE_VALUES:
                    if re.search(r'^\s*({})\s+\w'.format(value), line):
                        vote_lines.append(line)
                        break

        votes = find_columns_and_parse(vote_lines)
        for name, vcode in votes.items():
            if name == 'Mr. Speaker':
                name = self.metadata['session_details'][session]['speaker']
            elif name == 'Mr. President':
                name = self.metadata['session_details'][session]['president']
            if vcode == 'Y':
                yes_votes.append(name)
            elif vcode == 'N':
                no_votes.append(name)
            else:
                other_vote_detail[vcode].append(name)
                other_count += 1
                if vcode == 'P':
                    present_votes.append(name)
        # fake the counts
        if yes_count == 0 and no_count == 0 and present_count == 0:
            yes_count = len(yes_votes)
            no_count = len(no_votes)
        else:  # audit
            if yes_count != len(yes_votes):
                self.warning("Mismatched yes count [expect: %i] [have: %i]" % (yes_count, len(yes_votes)))
                warned = True
            if no_count != len(no_votes):
                self.warning("Mismatched no count [expect: %i] [have: %i]" % (no_count, len(no_votes)))
                warned = True
            if present_count != len(present_votes):
                self.warning("Mismatched present count [expect: %i] [have: %i]" % (present_count, len(present_votes)))
                warned = True

        if passed is None:
            if chamber == 'lower':  # senate doesn't have these lines
                self.warning("No pass/fail word found; fall back to comparing yes and no vote.")
                warned = True
            passed = yes_count > no_count
        vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                    other_count, other_vote_detail=other_vote_detail)
        for name in yes_votes:
            vote.yes(name)
        for name in no_votes:
            vote.no(name)
        for other_type, names in other_vote_detail.iteritems():
            for name in names:
                vote.other(name)
        vote.add_source(href)

        if warned:
            self.warning("Warnings were issued. Best to check %s" % href)
        return vote

    def refine_sponsor_list(self, chamber, action, sponsor_list, bill_id):
        if action.lower().find('removed') != -1:
            return
        if action.startswith('Chief'):
            self.debug("[%s] Assuming we already caught 'chief' for %s" % (bill_id, action))
            return
        match = SPONSOR_REFINE_PATTERN.match(action)
        if match:
            if match.groupdict()['title'] == 'Rep':
                chamber = 'lower'
            else:
                chamber = 'upper'
            for i, tup in enumerate(sponsor_list):
                spontype, sponsor, this_chamber, otype = tup
                if this_chamber == chamber and sponsor == match.groupdict()['name']:
                    try:
                        sponsor_list[i] = (SPONSOR_TYPE_REFINEMENTS[match.groupdict()['spontype']], sponsor, this_chamber, match.groupdict()['spontype'])
                    except KeyError:
                        self.warning('[%s] Unknown sponsor refinement type [%s]' % (bill_id, match.groupdict()['spontype']))
                    return
            self.warning("[%s] Couldn't find sponsor [%s,%s] to refine" % (bill_id, chamber, match.groupdict()['name']))
        else:
            self.debug("[%s] Don't know how to refine [%s]" % (bill_id, action))


def find_columns_and_parse(vote_lines):
    columns = find_columns(vote_lines)
    votes = {}
    for line in vote_lines:
        for idx in reversed(columns):
            bit = line[idx:]
            line = line[:idx]
            if bit:
                vote, name = bit.split(' ', 1)
                votes[name.strip()] = vote
    return votes


def _is_potential_column(line, i):
    for val in VOTE_VALUES:
        if re.search(r'^%s\s{2,10}(\w.).*' % val, line[i:]):
            return True
    return False


def find_columns(vote_lines):
    potential_columns = []

    for line in vote_lines:
        pcols = set()
        for i, x in enumerate(line):
            if _is_potential_column(line, i):
                pcols.add(i)
        potential_columns.append(pcols)

    starter = potential_columns[0]
    for pc in potential_columns[1:-1]:
        starter.intersection_update(pc)
    last_row_cols = potential_columns[-1]
    if not last_row_cols.issubset(starter):
        raise Exception("Row's columns [%s] don't align with candidate final columns [%s]: %s" % (last_row_cols, starter, line))
    # we should now only have values that appeared in every line
    return sorted(starter)


def build_sponsor_list(sponsor_atags):
    """return a list of (spontype,sponsor,chamber,official_spontype) tuples"""
    sponsors = []
    house_chief = senate_chief = None
    spontype = 'cosponsor'
    for atag in sponsor_atags:
        sponsor = atag.text
        if 'house' in atag.attrib['href'].split('/'):
            chamber = 'lower'
        elif 'senate' in atag.attrib['href'].split('/'):
            chamber = 'upper'
        else:
            chamber = None
        if chamber == 'lower' and house_chief is None:
            spontype = 'primary'
            official_spontype = 'chief'
            house_chief = sponsor
        elif chamber == 'upper' and senate_chief is None:
            spontype = 'primary'
            official_spontype = 'chief'
            senate_chief = sponsor
        else:
            spontype = 'cosponsor'
            official_spontype = 'cosponsor'  # until replaced
        sponsors.append((spontype, sponsor, chamber, official_spontype))
    return sponsors
