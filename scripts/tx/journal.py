import lxml.etree
import re

from get_legislation import TXLegislationScraper

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import Vote

def clean(root):
    # Remove page breaks
    for el in root.xpath(u'//p[contains(., "HOUSE JOURNAL \u2014") or contains(., "81st LEGISLATURE \u2014")] | //hr[@noshade and @size=1]'):
        el.getparent().remove(el)

    # Remove empty paragraphs
    for el in root.xpath('//p[not(node())]'):
        if el.tail and el.tail != '\r\n' and el.getprevious() is not None:
            el.getprevious().tail = el.tail
        el.getparent().remove(el)

def names(el):
    text = el.text + el.tail
    names = [name.strip() for name in text.split(';') if name.strip()]

    # First name will have stuff to ignore before an mdash
    names[0] = names[0].split(u'\u2014')[1].strip()
    # Get rid of trailing '.'
    names[-1] = names[-1][0:-1]

    return names

def votes(root):
    for el in root.xpath(u'//p[starts-with(., "Yeas \u2014")]'):
        text = ''.join(el.getprevious().itertext())
        m = re.search(r'(\w+ \d+) was adopted by \(Record (\d+)\): (\d+) Yeas, (\d+) Nays, (\d+) Present', text)
        if m:
            yes_count = int(m.group(3))
            no_count = int(m.group(4))
            other_count = int(m.group(5))

            vote = Vote('lower', None, 'final passage', True,
                        yes_count, no_count, other_count)
            vote['bill_id'] = m.group(1)
            vote['session'] = '81'
            vote['record'] = m.group(2)
            vote['filename'] = m.group(2)

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

def parse(f, scraper):
    root = lxml.etree.parse(f, lxml.etree.HTMLParser())
    clean(root)
    for vote in votes(root):
        scraper._add_standalone_vote(vote)

if __name__ == '__main__':
    # Test run
    scraper = TXLegislationScraper()
    try:
        f = open('81RDAY85FINAL.HTM')
    except:
        import urllib2
        f = urllib2.urlopen('http://www.journals.house.state.tx.us/hjrnl/81r/html/81RDAY85FINAL.HTM')

    parse(f, scraper)
