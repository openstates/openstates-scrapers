import lxml.etree
import re
import datetime
import sys
import os
import urlparse
from cStringIO import StringIO as StringIO
from get_legislation import TXLegislationScraper, parse_ftp_listing
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import Vote


def clean(root):
    # Remove page breaks
    for el in root.xpath('//hr[@noshade and @size=1]'):
        parent = el.getparent()
        previous = el.getprevious()
        if previous and previous.text and previous.text.find("JOURNAL") != -1:
            parent.remove(previous)
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
    names = [name.strip() for name in text.split(';') if name.strip()]

    # First name will have stuff to ignore before an mdash
    names[0] = names[0].split(u'\u2014')[1].strip()
    # Get rid of trailing '.'
    names[-1] = names[-1][0:-1]

    return names


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

            type = m.group('type')
            if type == 'adopted' or type == 'passed':
                type = 'final passage'
            else:
                type = 'to ' + m.group('to')

            vote = Vote(None, None, type, True,
                        yes_count, no_count, other_count)
            vote['bill_id'] = m.group('bill_id')
            vote['session'] = '81'
            vote['method'] = 'record'
            vote['record'] = m.group('record')
            vote['filename'] = m.group('record')

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
     for el in root.xpath(u'//p[starts-with(., "All Members are deemed")]'):
         text = ''.join(el.getprevious().itertext())
         text.replace('\n', ' ')
         m = re.search(r'(?P<bill_id>\w+\W+\d+)(,\W+as\W+amended,)?\W+was\W+'
                       '(?P<type>adopted|passed'
                       '(\W+to\W+(?P<to>engrossment|third\W+reading))?)\W+'
                       'by\W+a\W+viva\W+voce\W+vote', text)
         if m:
             type = m.group('type')
             if type == 'adopted' or type == 'passed':
                 type = 'final passage'
             else:
                 type = 'to ' + m.group('to')

             # No identifier, generate our own
             record = str(uuid.uuid1())

             vote = Vote(None, None, type, True, 0, 0, 0)
             vote['bill_id'] = m.group('bill_id')
             vote['session'] = '81'
             vote['method'] = 'viva voce'
             vote['filename'] = record
             vote['record'] = record
             yield vote

def parse(url, chamber, scraper):
    with scraper.urlopen_context(url) as page:
        root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
        clean(root)

        title = root.find('head/title').text
        date_string = title.split('-')[0].strip()
        date = datetime.datetime.strptime(date_string, "%A, %B %d, %Y")

        for vote in votes(root):
            vote['date'] = date
            vote['chamber'] = chamber
            scraper._add_standalone_vote(vote)

if __name__ == '__main__':
    # Test run
    scraper = TXLegislationScraper()

    ftp_root = "ftp://ftp.legis.state.tx.us/journals/"
    for session in ['81R', '811']:
        session_root = urlparse.urljoin(ftp_root, session + '/html/', True)

        house_root = urlparse.urljoin(session_root, 'house/', True)
        with scraper.urlopen_context(house_root) as listing:
            for name in parse_ftp_listing(listing):
                if name.startswith('INDEX'):
                    continue
                url = urlparse.urljoin(house_root, name)
                parse(url, 'lower', scraper)

        senate_root = urlparse.urljoin(session_root, 'senate/', True)
        with scraper.urlopen_context(senate_root) as listing:
            for name in parse_ftp_listing(listing):
                if name.startswith('INDEX'):
                    continue
                url = urlparse.urljoin(senate_root, name)
                parse(url, 'upper', scraper)
