
import re
from itertools import dropwhile, takewhile
from collections import defaultdict

import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee

committee_urls = {
    'lower': {
        2011: 'http://leg.mt.gov/css/House/house-committees-2011.asp',
        },

    'upper': {
        2011: 'http://leg.mt.gov/css/Senate/senate%20committees-2011.asp',
        }
    }


class MTCommitteeScraper(CommitteeScraper):

    state = 'mt'

    def scrape(self, chamber, term):
        for tdata in self.metadata['terms']:
            if term == tdata['name']:
                year = tdata['start_year']
                break

        url = committee_urls[chamber][year]
        html = self.urlopen(url, use_cache_first=True)

        for name_dict, c in scrape_committees(html, year, chamber,
                                              url, save=True):
            self.save_committee(c)


def scrape_committees(html, year, chamber, url, save=False):
    '''Since the legislator names aren't properly capitalized in the
    csv file, scrape the committee page and use the names listed there
    instead.
    '''
    name_dict = defaultdict(set)
    html = html.decode('latin-1')
    doc = lxml.html.fromstring(html)
    tds = doc.xpath('//td[@valign="top"]')[3:]

    cache = []
    for td in tds:
        for name_dict, c in _committees_td(td, chamber, url, name_dict):
            if c not in cache:
                cache.append(c)
                yield name_dict, c


def _committees_td(el, chamber, url, name_dict):

    edge = '      '
    until_edge = lambda s: s != edge

    # Toss preliminary junk.
    itertext = dropwhile(until_edge, el.itertext())

    committees_data = []
    failures = 0
    while True:

        # Get next chunk of committee data.
        data = list(takewhile(until_edge, itertext))
        if not data:
            if failures > 5:
                break
            else:
                failures += 1
                continue

        committees_data.append(data)

    for data in committees_data:
        c = _committee_data(data, chamber, url, name_dict)
        if c:
            yield c


def _committee_data(lines, chamber, url, name_dict):

    name_pattern = r'\s{,20}(?:(.+)\:)?\s{,20}(.+?) \((?:\w\-(.+))\)'

    # Functions to identify unused data.
    junk = [lambda s: s != 'On Call',
            lambda s: 'Staff:' not in s,
            lambda s: 'Secreetary:' not in s,
            lambda s: s.strip(),
            lambda s: not s.isupper()]

    # Toss unused data.
    for j in junk:
        lines = filter(j, lines)

    lines = lines[::-1]
    kw = {'chamber': chamber}

    kw['committee'] = lines.pop().strip()

    if not lines:
        return

    if lines[-1].startswith('Meets'):
        kw['meetings_info'] = lines.pop().strip()

    c = Committee(**kw)

    for name in lines[2:]:
        m = re.search(name_pattern, name)
        if m:
            title, name, city = m.groups()
            if title:
                title = title.lower()
            name_dict[city.lower()].add(name)
            c.add_member(name, role=(title or 'member'))

    c.add_source(url)

    return name_dict, c
