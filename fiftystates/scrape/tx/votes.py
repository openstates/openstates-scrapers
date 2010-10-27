import re
import uuid
import urlparse
import datetime

from fiftystates.scrape.votes import VoteScraper, Vote
from fiftystates.scrape.tx.utils import parse_ftp_listing

import lxml.etree


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

    # First name will have stuff to ignore before an mdash
    names[0] = names[0].split(u'\u2014')[1].strip()
    # Get rid of trailing '.'
    names[-1] = names[-1][0:-1]

    return names


def get_motion(match):
    if match.group('type') == 'passed' or match.group('type') == 'adopted':
        return 'final passage'
    else:
        return 'to ' + match.group('to')


def get_type(motion):
    if motion == 'final passage':
        return 'passage'
    else:
        return 'other'


def votes(root):
    for vote in record_votes(root):
        yield vote
    for vote in viva_voce_votes(root):
        yield vote


def record_votes(root):
    for el in root.xpath(u'//p[starts-with(., "Yeas \u2014")]'):
        text = ''.join(el.getprevious().itertext())
        text.replace('\n', ' ')
        m = re.search(r'(?P<bill_id>\w+\W+\d+)(,?\W+as\W+amended,?)?\W+was\W+'
                      '(?P<type>adopted|passed'
                      '(\W+to\W+(?P<to>engrossment|third\W+reading))?)\W+'
                      'by\W+\(Record\W+(?P<record>\d+)\):\W+'
                      '(?P<yeas>\d+)\W+Yeas,\W+(?P<nays>\d+)\W+Nays,\W+'
                      '(?P<present>\d+)\W+Present', text)
        if m:
            yes_count = int(m.group('yeas'))
            no_count = int(m.group('nays'))
            other_count = int(m.group('present'))

            bill_id = m.group('bill_id')
            if bill_id.startswith('H') or bill_id.startswith('CSHB'):
                bill_chamber = 'lower'
            elif bill_id.startswith('S') or bill_id.startswith('CSSB'):
                bill_chamber = 'upper'
            else:
                continue

            motion = get_motion(m)

            vote = Vote(None, None, motion, True,
                        yes_count, no_count, other_count)
            vote['bill_id'] = bill_id
            vote['bill_chamber'] = bill_chamber
            vote['session'] = '81'
            vote['method'] = 'record'
            vote['record'] = m.group('record')
            vote['filename'] = m.group('record')
            vote['type'] = get_type(motion)

            for name in names(el):
                vote.yes(name)

            el = el.getnext()
            if el.text and el.text.startswith('Nays'):
                for name in names(el):
                    vote.no(name)
                el = el.getnext()

            while el.text and re.match(r'Present|Absent', el.text):
                for name in names(el):
                    vote.other(name)
                el = el.getnext()

            vote['other_count'] = len(vote['other_votes'])
            yield vote
        else:
            pass


def viva_voce_votes(root):
    prev_id = None
    for el in root.xpath(u'//p[starts-with(., "All Members are deemed")]'):
        text = ''.join(el.getprevious().itertext())
        text.replace('\n', ' ')
        m = re.search(r'(?P<bill_id>\w+\W+\d+)(,\W+as\W+amended,)?\W+was\W+'
                      '(?P<type>adopted|passed'
                      '(\W+to\W+(?P<to>engrossment|third\W+reading))?)\W+'
                      'by\W+a\W+viva\W+voce\W+vote', text)
        if m:
            motion = get_motion(m)

            # No identifier, generate our own
            record = str(uuid.uuid1())

            bill_id = m.group('bill_id')
            if bill_id.startswith('H') or bill_id.startswith('CSHB'):
                bill_chamber = 'lower'
            elif bill_id.startswith('S') or bill_id.startswith('CSSB'):
                bill_chamber = 'upper'
            else:
                continue

            vote = Vote(None, None, motion, True, 0, 0, 0)
            vote['bill_id'] = bill_id
            vote['bill_chamber'] = bill_chamber
            vote['session'] = '81'
            vote['method'] = 'viva voce'
            vote['filename'] = record
            vote['record'] = record
            vote['type'] = get_type(motion)
            yield vote
            continue

        m = re.search('The\W+bill\W+was.+and\W+was\W+'
                      '(?P<type>adopted|passed'
                      '(\W+to\W+(?P<to>engrossment|third\W+reading))?)\W+'
                      'by\W+a\W+viva\W+voce\W+vote', text)
        if m:
            prev_text = ''.join(el.getprevious().getprevious().itertext())
            m2 = re.match('(HB|SB|CSHB|CSSB|HR|SR)\W+\d+', prev_text)
            if m2:
                bill_id = m2.group()
                prev_id = bill_id
            else:
                # This is scary
                bill_id = prev_id

            if not bill_id:
                continue

            if bill_id.startswith('H') or bill_id.startswith('CSHB'):
                bill_chamber = 'lower'
            elif bill_id.startswith('S') or bill_id.startswith('CSSB'):
                bill_chamber = 'upper'
            else:
                continue

            motion = get_motion(m)

            record = str(uuid.uuid1())
            vote = Vote(None, None, motion, True, 0, 0, 0)
            vote['bill_id'] = bill_id
            vote['bill_chamber'] = bill_chamber
            vote['session'] = '81'
            vote['method'] = 'viva voce'
            vote['filename'] = record
            vote['record'] = record
            vote['type'] = get_type(motion)

            yield vote
            continue


class TXVoteScraper(VoteScraper):
    state = 'tx'
    _ftp_root = 'ftp://ftp.legis.state.tx.us/'

    def scrape(self, chamber, session):
        self.validate_session(session)

        if len(session) == 2:
            session = "%sR" % session

        journal_root = urlparse.urljoin(self._ftp_root, ("/journals/" +
                                                         session +
                                                         "/html/"),
                                        True)

        if chamber == 'lower':
            journal_root = urlparse.urljoin(journal_root, "house/", True)
        else:
            journal_root = urlparse.urljoin(journal_root, "senate/", True)

        with self.urlopen(journal_root) as listing:
            for name in parse_ftp_listing(listing):
                if not name.startswith('81'):
                    continue
                url = urlparse.urljoin(journal_root, name)
                self.scrape_journal(url, chamber)

    def scrape_journal(self, url, chamber):
        with self.urlopen(url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            clean_journal(root)

            title = root.find('head/title').text
            date_string = title.split('-')[0].strip()
            date = datetime.datetime.strptime(
                date_string, "%A, %B %d, %Y").date()

            for vote in votes(root):
                vote['date'] = date
                vote['chamber'] = chamber
                vote.add_source(url)
                self.save_vote(vote)
