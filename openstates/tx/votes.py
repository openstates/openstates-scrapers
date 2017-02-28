import os
import re
import uuid
import urlparse
import datetime
import scrapelib
import collections

import lxml.html
from billy.scrape.votes import VoteScraper, Vote

import tx


def prev_tag(el):
    """
    Return previous tag, skipping <br>s.
    """
    el = el.getnext()
    while el.tag == 'br':
        el = el.getnext()
    return el


def next_tag(el):
    """
    Return next tag, skipping <br>s.
    """
    el = el.getnext()
    while el.tag == 'br':
        el = el.getnext()
    return el


def clean_journal(root):
    # Remove page breaks
    for el in root.xpath('//hr[@noshade and @size=1]'):
        parent = el.getparent()
        previous = el.getprevious()
        if previous:
            parent.remove(previous)
        parent.remove(el)

    # Does lxml not support xpath ends-with?
    for el in root.xpath("//p[contains(text(), 'REGULAR SESSION')]"):
        if el.text.endswith("REGULAR SESSION"):
            parent = el.getparent()
            parent.remove(el)

    for el in root.xpath("//p[contains(text(), 'JOURNAL')]"):
        if (("HOUSE JOURNAL" in el.text or "SENATE JOURNAL" in el.text) and
            "Day" in el.text):

            parent = el.getparent()
            parent.remove(el)

    # Remove empty paragraphs
    for el in root.xpath('//p[not(node())]'):
        if el.tail and el.tail != '\r\n' and el.getprevious() is not None:
            el.getprevious().tail = el.tail
        el.getparent().remove(el)

    # Journal pages sometimes replace spaces with <font color="White">i</font>
    # (or multiple i's for bigger spaces)
    for el in root.xpath('//font[@color="White"]'):
        if el.text:
            el.text = ' ' * len(el.text)


def names(el):
    text = (el.text or '') + (el.tail or '')

    names = []
    for name in text.split(';'):
        name = name.strip().replace('\r\n', '').replace('  ', ' ')

        if not name:
            continue

        if name == 'Gonzalez Toureilles':
            name = 'Toureilles'
        elif name == 'Mallory Caraway':
            name = 'Caraway'
        elif name == 'Martinez Fischer':
            name = 'Fischer'
        elif name == 'Rios Ybarra':
            name = 'Ybarra'

        names.append(name)

    if names:
        # First name will have stuff to ignore before an mdash
        names[0] = clean_name(names[0]).strip()
        # Get rid of trailing '.'
        names[-1] = names[-1][0:-1]

    return names


def clean_name(name):
    return re.split(ur'[\u2014:]', name)[-1]


def votes(root, session):
    for vote in record_votes(root, session):
        yield vote
    for vote in viva_voce_votes(root, session):
        yield vote


def first_int(res):
    if res is not None:
        return int(next(group for group in res.groups() if group is not None))


class BaseVote(object):

    def __init__(self, el):
        self.el = el

    @property
    def text(self):
        return self.el.text_content()

    @property
    def previous(self):
        return self.el.getprevious().getprevious()

    @property
    def next(self):
        return self.el.getnext().getnext()

    @property
    def is_valid(self):
        return (
            self.bill_id is not None and
            self.chamber is not None
        )

    @property
    def bill_id(self):
        bill_id = (
            get_bold_text(self.el) or
            get_bold_text(self.previous)
        )
        return clean_bill_id(bill_id)

    @property
    def chamber(self):
        bill_id = self.bill_id or ''
        if bill_id.startswith('H') or bill_id.startswith('CSHB'):
            return 'lower'
        if bill_id.startswith('S') or bill_id.startswith('CSSB'):
            return 'upper'


# Note: Vote count patterns are inconsistent across journals and may follow the
# pattern "145 Yeas, 0 Nays" (http://www.journals.house.state.tx.us/HJRNL/85R/HTML/85RDAY02FINAL.HTM)
# or "Yeas 20, Nays 10" (http://www.journals.senate.state.tx.us/SJRNL/85R/HTML/85RSJ02-08-F.HTM)
class MaybeVote(BaseVote):
    yeas_pattern = re.compile(r'yeas[\s\xa0]+(\d+)|(\d+)[\s\xa0]+yeas', re.IGNORECASE)
    nays_pattern = re.compile(r'nays[\s\xa0]+(\d+)|(\d+)[\s\xa0]+nays', re.IGNORECASE)
    present_pattern = re.compile(r'present[\s\xa0]+(\d+)|(\d+)[\s\xa0]+present', re.IGNORECASE)
    record_pattern = re.compile(r'\(record[\s\xa0]+(\d+)\)', re.IGNORECASE)
    passed_pattern = re.compile(r'(adopted|passed|prevailed)', re.IGNORECASE)
    check_prev_pattern = re.compile(r'the (motion|resolution)', re.IGNORECASE)
    votes_pattern = re.compile(r'^(yeas|nays|present|absent)', re.IGNORECASE)
    amendment_pattern = re.compile(r'the amendment to', re.IGNORECASE)

    @property
    def is_valid(self):
        return (
            super(MaybeVote, self).is_valid and
            self.yeas is not None and
            self.nays is not None
        )

    @property
    def is_amendment(self):
        return self.amendment_pattern.search(self.text) is not None

    @property
    def passed(self):
        return bool(self.passed_pattern.search(self.text))

    @property
    def yeas(self):
        res = self.yeas_pattern.search(self.text)
        return first_int(res)

    @property
    def nays(self):
        res = self.nays_pattern.search(self.text)
        return first_int(res)

    @property
    def present(self):
        res = self.present_pattern.search(self.text)
        return first_int(res)

    @property
    def record(self):
        res = self.record_pattern.search(self.text)
        return first_int(res)

    @property
    def votes(self):
        votes = collections.defaultdict(list)
        el = next_tag(self.el)
        while el.text:
            res = re.match(self.votes_pattern, el.text)
            if not res:
                break
            votes[res.groups()[0].lower()].extend(names(el))
            el = next_tag(el)
        return votes


class MaybeViva(BaseVote):
    amendment_pattern = re.compile(r'the amendment to', re.IGNORECASE)
    floor_amendment_pattern = re.compile(r'floor amendment no', re.IGNORECASE)
    passed_pattern = re.compile(r'(adopted|passed|prevailed)', re.IGNORECASE)
    viva_voce_pattern = re.compile(r'viva voce vote', re.IGNORECASE)

    @property
    def is_valid(self):
        return (
            super(MaybeViva, self).is_valid and
            self.viva_voce_pattern.search(self.previous.text_content()) is not None
        )

    @property
    def is_amendment(self):
        return bool(
            self.amendment_pattern.search(self.previous.text_content()) or
            self.floor_amendment_pattern.search(self.text)
        )

    @property
    def passed(self):
        return bool(self.passed_pattern.search(self.text))


def get_bold_text(el):
    b = el.find('b')
    if b is not None:
        return b.text_content()


def clean_bill_id(bill_id):
    if bill_id:
        bill_id = bill_id.replace(u'\xa0', ' ')
        bill_id = re.sub(r'CS(SB|HB)', r'\1', bill_id)
    return bill_id


vote_selectors = [
    '[@class = "textpara"]',
    '[contains(translate(., "YEAS", "yeas"), "yeas")]',
]
def record_votes(root, session):
    for el in root.xpath('//div{}'.format(''.join(vote_selectors))):
        mv = MaybeVote(el)
        if not mv.is_valid:
            continue

        v = Vote(None, None, 'passage' if mv.passed else 'other', mv.passed,
                 mv.yeas or 0, mv.nays or 0, mv.present or 0)
        v['bill_id'] = mv.bill_id
        v['bill_chamber'] = mv.chamber
        v['is_amendment'] = mv.is_amendment
        v['session'] = session[0:2]
        v['method'] = 'record'

        for each in mv.votes['yeas']:
            v.yes(each)
        for each in mv.votes['nays']:
            v.no(each)
        for each in mv.votes['present'] + mv.votes['absent']:
            v.other(each)

        yield v


def viva_voce_votes(root, session):
    prev_id = None
    for el in root.xpath(u'//div[starts-with(., "All Members are deemed")]'):
        mv = MaybeViva(el)
        if not mv.is_valid:
            continue

        v = Vote(None, None, 'passage' if mv.passed else 'other', mv.passed, 0, 0, 0)
        v['bill_id'] = mv.bill_id
        v['bill_chamber'] = mv.chamber
        v['is_amendment'] = mv.is_amendment
        v['session'] = session[0:2]
        v['method'] = 'viva voce'

        yield v


class TXVoteScraper(VoteScraper):
    jurisdiction = 'tx'
    #the 84th session doesn't seem to be putting journals on the ftp

    _ftp_root = 'ftp://ftp.legis.state.tx.us/'

    def scrape(self, chamber, session):
        self.validate_session(session)

        if session == '821':
            self.warning('no journals for session 821')
            return

        if len(session) == 2:
            session = "%sR" % session

        #As of 1/30/15, the 84th session does not have journals on the ftp
        """
        journal_root = urlparse.urljoin(self._ftp_root, ("/journals/" +
                                                         session +
                                                         "/html/"),
                                        True)

        if chamber == 'lower':
            journal_root = urlparse.urljoin(journal_root, "house/", True)
        else:
            journal_root = urlparse.urljoin(journal_root, "senate/", True)

        listing = self.get(journal_root).text
        for name in parse_ftp_listing(listing):
            if not name.startswith(session):
                continue
            url = urlparse.urljoin(journal_root, name)
            self.scrape_journal(url, chamber, session)
        """
        #we're going to go through every day this year before today
        #and see if there were any journals that day
        today = datetime.datetime.today()
        today = datetime.datetime(today.year, today.month, today.day)
        journal_day = datetime.datetime(today.year, 1, 1)
        day_num = 1
        while journal_day <= today:
            if chamber == 'lower':
                journal_root = "http://www.journals.house.state.tx.us/HJRNL/%s/HTML/" % session
                journal_url = journal_root + session + "DAY" + str(day_num).zfill(2)+"FINAL.HTM"
            else:
                journal_root = "http://www.journals.senate.state.tx.us/SJRNL/%s/HTML/" % session
                journal_url = journal_root + "%sSJ%s-%s-F.HTM" % (session,str(journal_day.month).zfill(2), str(journal_day.day).zfill(2))
            journal_day += datetime.timedelta(days=1)
            day_num += 1

            try:
                self.get(journal_url)
            except scrapelib.HTTPError:
                continue
            else:
                self.scrape_journal(journal_url, chamber, session)

    def scrape_journal(self, url, chamber, session):
        if "R" in session:
            session_num = session.strip("R")
        else:
            session_num = session
        year = tx.metadata['session_details'][session_num]['start_date'].year
        try:
            page = self.get(url).text
        except scrapelib.HTTPError:
            return

        root = lxml.html.fromstring(page)
        clean_journal(root)

        if chamber == 'lower':
            div = root.xpath("//div[@class = 'textpara']")[0]
            date_str = " ".join(div.text.split()[-4:]).strip()
            date = datetime.datetime.strptime(
                date_str, "%A, %B %d, %Y").date()
        else:
            fname = os.path.split(urlparse.urlparse(url).path)[-1]
            date_str = re.match(r'%sSJ(\d\d-\d\d).*\.HTM' % session,
                            fname).group(1) + " %s" % year
            date = datetime.datetime.strptime(date_str,
                                              "%m-%d %Y").date()

        for vote in votes(root, session):
            vote['date'] = date
            vote['chamber'] = chamber
            vote.add_source(url)
            self.save_vote(vote)
