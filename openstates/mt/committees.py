'''
This file has a slightly unusual structure. The urs and the main
scrape function are defined at the top level because the legislator
scrape requires data from the committee pages in order to get
properly capitalized names. So that part needs to be importable and
hence the need to dcouple it from the scraper instance. If that makes
sense.

This file currently scrapes only standing committees and doesn't
bother with the arguably important joint appropriations subcomittees,
Which contain members of the appropriations committees from each
and deal with budgetary matters.
'''
import re
from itertools import dropwhile, takewhile
from collections import defaultdict

import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee
import scrapelib


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

        for name_dict, c in scrape_committees(year, chamber):
            self.save_committee(c)


def scrape_committees(year, chamber):
    '''Since the legislator names aren't properly capitalized in the
    csv file, scrape the committee page and use the names listed there
    instead.
    '''
    url = committee_urls[chamber][year]
    html = scrapelib.urlopen(url).decode('latin-1')

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
    '''Get all committees data from a particular td in the
    comittees page.
    '''
    edge = '      '
    predicate = lambda s: s != edge

    # Toss preliminary junk.
    itertext = dropwhile(predicate, el.itertext())

    committees_data = []
    failures = 0
    while True:

        # Get next chunk of committee data.
        data = list(takewhile(predicate, itertext))

        # A hack to accomodate the different, kooky html for the
        # Business and Labor committee.
        if 'Business & Labor' in data:
            data += list(takewhile(predicate, itertext))

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
    '''Given a list of lines of committee data from a td element
    on the committees page, extract the commitee name, the members,
    and yeild a committee object. Also yield the name dict incase
    the calling function needs it for something.
    '''
    name_pattern = r'\s{,20}(?:(.+)\:)?\s{,20}(.+?) \((?:\w\-(.+))\)'

    # Functions to identify unused data.
    junk = [lambda s: s != 'On Call',
            lambda s: 'Staff:' not in s,
            lambda s: 'Secretary:' not in s,
            lambda s: s.strip(),
            lambda s: not s.isupper()]

    # Toss unused data.
    for j in junk:
        lines = filter(j, lines)

    if len(lines) < 2:
        return

    lines = lines[::-1]
    kw = {'chamber': chamber}
    kw['committee'] = lines.pop().strip()

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
