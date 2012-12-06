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
        },

    'joint': {
        2011: 'http://leg.mt.gov/css/Sessions/62nd/joint%20subcommittees.asp',
        }
    }


class MTCommitteeScraper(CommitteeScraper):

    jurisdiction = 'mt'

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
    html = scrapelib.urlopen(url)

    name_dict = defaultdict(set)
    doc = lxml.html.fromstring(html)
    tds = doc.xpath('//td[@valign="top"]')[3:]

    cache = []
    for td in tds:
        for name_dict, c in _committees_td(td, chamber, url, name_dict):
            if c not in cache:
                cache.append(c)
                yield name_dict, c

    # Get the joint approps subcommittees during the upper scrape.
    if chamber == 'upper':
        url = committee_urls['joint'][year]
        html = scrapelib.urlopen(url)

        name_dict = defaultdict(set)
        doc = lxml.html.fromstring(html)
        tds = doc.xpath('//td[@valign="top"]')[3:]

        cache = []
        for td in tds:
            for name_dict, c in _committees_td(td, 'joint', url, name_dict):
                if c not in cache:
                    cache.append(c)

                    # These are subcommittees, so a quick switcheroo of the names:
                    c['subcommittee'] = c['committee']
                    c['committee'] = 'Appropriations'
                    yield name_dict, c


def _committees_td(el, chamber, url, name_dict):
    '''Get all committees data from a particular td in the
    comittees page.
    '''
    edge = '      '

    # The unreliable HTML (dreamweaver...) is different on upper/lower pages.
    if chamber == 'lower':
        not_edge = lambda s: (s != edge and s != 'PDF Version')
        is_edge = lambda s: (s == edge or s == 'PDF Version')
        predicate = lambda s: ('Secretary:' not in s)

    if chamber == 'upper':
        not_edge = lambda s: s != edge
        is_edge = lambda s: s == edge
        predicate = not_edge

    if chamber == 'joint':
        not_edge = lambda s: not s.strip().startswith('Education')
        is_edge = lambda s: s == edge
        predicate = lambda s: ('Secretary:' not in s)

    itertext = el.itertext()

    # Toss preliminary junk.
    itertext = dropwhile(not_edge, itertext)

    committees_data = []
    failures = 0
    while True:

        # Drop any leading "edge"
        itertext = dropwhile(is_edge, itertext)

        # Get the rest of committee data.
        data = list(takewhile(predicate, itertext))

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
    name_pattern = r'\s{,20}(?:(.+)\:)?\s{,20}(.+?) \((?:\w\-([^)]+))'

    # Functions to identify unused data.
    junk = [lambda s: s != 'On Call',
            lambda s: 'Staff:' not in s,
            lambda s: 'Secretary:' not in s,
            lambda s: s.strip(),
            lambda s: not s.isupper()]

    # Toss unused data.
    for j in junk:
        lines = filter(j, lines)

    if (len(lines) < 2) or (u'\xa0' in lines):
        return

    lines = lines[::-1]
    kw = {'chamber': chamber}
    kw['committee'] = lines.pop().strip()

    if lines[-1].startswith('Meets'):
        kw['meetings_info'] = lines.pop().strip()

    c = Committee(**kw)

    for name in reversed(lines):
        kwargs = {}
        m = re.search(name_pattern, name)
        if m:
            title, name, city = m.groups()
            if title:
                title = title.lower()
            house = re.search(r'(Sen\.|Rep\.)\s+', name)
            if house:
                house = house.group()
                if 'Sen.' in house:
                    kwargs['chamber'] = 'upper'
                elif 'Rep.' in house:
                    kwargs['chamber'] = 'lower'
                name = name.replace(house, '').strip()
            name_dict[city.lower()].add(name)
            c.add_member(name, role=(title or 'member'), **kwargs)

    c.add_source(url)

    return name_dict, c
