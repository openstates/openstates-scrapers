import lxml.etree
import re

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
            print "%s was adopted by %s" % (m.group(1), m.group(2))
            yes_count = int(m.group(3))
            no_count = int(m.group(4))
            other_count = int(m.group(5))
            print '%d yeas, %d nays, %d other' % (yes_count,
                                                  no_count,
                                                  other_count)
            vote = Vote('lower', None, 'final passage', True,
                        yes_count, no_count, other_count)

            for name in names(el):
                vote.yes(name)
            for name in names(el.getnext()):
                vote.no(name)
            for name in names(el.getnext().getnext()):
                vote.other(name)

            yield vote
        else:
            pass

def parse(f):
    root = lxml.etree.parse(f, lxml.etree.HTMLParser())
    clean(root)
    for vote in votes(root):
        pass

if __name__ == '__main__':
    # Test run
    try:
        f = open('81RDAY85FINAL.HTM')
    except:
        import urllib2
        f = urllib2.urlopen('http://www.journals.house.state.tx.us/hjrnl/81r/html/81RDAY85FINAL.HTM')

    parse(f)
