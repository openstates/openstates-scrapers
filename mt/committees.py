# -*- coding: utf-8 -*-
'''
This file has a slightly unusual structure. The urs and the main
scrape function are defined at the top level because the legislator
scrape requires data from the committee pages in order to get
properly capitalized names. So that part needs to be importable and
hence the need to dcouple it from the scraper instance. If that makes
sense.'''
import re
from itertools import dropwhile, takewhile
from collections import defaultdict

import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee
from billy.scrape.utils import convert_pdf
import scrapelib


committee_urls = {
    'lower': {
        2011: 'http://leg.mt.gov/css/House/house-committees-2011.asp',
        2013: 'http://leg.mt.gov/content/Committees/Session/2013%20house%20committees%20-%20columns.pdf',
        2015: 'http://leg.mt.gov/content/Sessions/64th/2015-house-committees.pdf',
        },

    'upper': {
        2011: 'http://leg.mt.gov/css/Senate/senate%20committees-2011.asp',
        2013: 'http://leg.mt.gov/content/Committees/Session/2013%20senate%20committees%20-%20columns.pdf',
        2015: 'http://leg.mt.gov/content/Sessions/64th/2015-senate-committees.pdf',
        },

    'joint': {
        2011: 'http://leg.mt.gov/css/Sessions/62nd/joint%20subcommittees.asp',
        # 2013: 'http://leg.mt.gov/css/Sessions/62nd/joint%20subcommittees.asp',
        }
    }


class MTCommitteeScraper(CommitteeScraper):

    jurisdiction = 'mt'

    def scrape(self, chamber, term):
        '''Since the legislator names aren't properly capitalized in the
        csv file, scrape the committee page and use the names listed there
        instead.
        '''
        for tdata in self.metadata['terms']:
            if term == tdata['name']:
                year = tdata['start_year']
                break

        url = committee_urls[chamber][year]
        fn, response = self.urlretrieve(url)

        if response.headers['content-type'] == 'application/pdf':
            # The committee list is a pdf.
            self.scrape_committees_pdf(year, chamber, fn, url)

        else:
            # Here it's html.
            with open(fn) as f:
                doc = lxml.html.fromstring(response.text)
                for name_dict, c in scrape_committees_html(year, chamber, doc):
                    if c['members']:
                        self.save_committee(c)

    def scrape_committees_pdf(self, year, chamber, filename, url):
        if chamber == 'lower' and year == 2015:
            text = self._fix_house_text(filename)
        else:
            text = convert_pdf(filename, type='text-nolayout')

        for hotgarbage, replacement in (
            (r'Judicial Branch, Law Enforcement,\s+and\s+Justice',
             'Judicial Branch, Law Enforcement, and Justice'),

            (r'Natural Resources and\s+Transportation',
             'Natural Resources and Transportation'),

            (r'(?u)Federal Relations, Energy,?\s+and\s+Telecommunications',
             'Federal Relations, Energy, and Telecommunications')
            ):
            text = re.sub(hotgarbage, replacement, text)

        lines = iter(text.splitlines())

        # Drop any lines before the ag committee.
        lines = dropwhile(lambda s: 'Agriculture' not in s, lines)

        def is_committee_name(line):
            if '(cont.)' in line.lower():
                return False
            for s in (
                'committee', ' and ', 'business', 'resources',
                'legislative', 'administration', 'government',
                'local', 'planning', 'judicial', 'natural',
                'resources', 'general', 'health', 'human',
                'education'):
                if s in line.lower():
                    return True
            if line.istitle() and len(line.split()) == 1:
                return True
            return False

        def is_legislator_name(line):
            return re.search(r'\([RD]', line)

        comm = None
        in_senate_subcommittees = False
        while True:
            try:
                line = lines.next()
            except StopIteration:
                break
            # Replace Unicode variants with ASCII equivalents
            line = line.replace(" ", " ").replace("‐", "-")

            if 'Subcommittees' in line:
                # These appear in both chambers' lists, so de-dup the scraping
                if chamber == 'lower':
                    break
                elif chamber == 'upper':
                    self.info("Beginning scrape of joint subcommittees")

                in_senate_subcommittees = True
                chamber = 'joint'
                continue

            if is_committee_name(line):
                subcommittee = None

                if in_senate_subcommittees:
                    committee = ('Joint Appropriations/Finance & Claims')
                    subcommittee = line.strip()
                else:
                    committee = line.strip()

                if comm and comm['members']:
                    self.save_committee(comm)

                comm = Committee(chamber, committee=committee,
                                 subcommittee=subcommittee)
                comm.add_source(url)

            elif is_legislator_name(line):
                name, party = line.rsplit('(', 1)
                name = name.strip().replace("Rep. ", "").replace("Sen. ", "")
                if re.search(' Ch', party):
                    role = 'chair'
                elif ' VCh' in party:
                    role = 'vice chair'
                elif ' MVCh' in party:
                    role = 'minority vice chair'
                else:
                    role = 'member'
                comm.add_member(name, role)

        if comm['members']:
            self.save_committee(comm)

    def _fix_house_text(self, filename):
        '''
        TLDR: throw out bad text, replace it using different parser
        settings.

        When using `pdftotext` on the 2015 House committee list,
        the second and third columns of the second page get mixed up,
        which makes it very difficult to parse. Adding the `--layout`
        option fixes this, but isn't worth switching all parsing to
        that since the standard `pdftotext --nolayout` is easier in all
        other cases.

        The best solution to this is to throw out the offending text,
        and replace it with the correct text. The third and fourth
        columns are joint comittees that are scraped from the Senate
        document, so the only column that needs to be inserted this way
        is the second.
        '''

        # Take the usable text from the normally-working parsing settings
        text = convert_pdf(filename, type='text-nolayout')
        assert "Revised: January 23, 2015" in text,\
            "House committee list has changed; check that the special-case"\
            " fix is still necessary, and that the result is still correct"
        text = re.sub(r'(?sm)Appropriations/F&C.*$', "", text)

        # Take the usable column from the alternate parser
        alternate_text = convert_pdf(filename, type='text')
        alternate_lines = alternate_text.split('\n')

        HEADER_OF_COLUMN_TO_REPLACE = "State Administration (cont.)      "
        (text_of_line_to_replace, ) = [
            x for x in alternate_lines
            if HEADER_OF_COLUMN_TO_REPLACE in x
        ]
        first_line_to_replace = alternate_lines.index(text_of_line_to_replace)
        first_character_to_replace = alternate_lines[
            first_line_to_replace].index(HEADER_OF_COLUMN_TO_REPLACE) - 1
        last_character_to_replace = (first_character_to_replace +
                                     len(HEADER_OF_COLUMN_TO_REPLACE))

        column_lines_to_add = [
            x[first_character_to_replace:last_character_to_replace]
            for x in alternate_lines[first_line_to_replace + 1:]
        ]
        column_text_to_add = '\n'.join(column_lines_to_add)

        text = text + column_text_to_add
        return text


def scrape_committees_html(year, chamber, doc):
    name_dict = defaultdict(set)
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
        html = scrapelib.get(url).text

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
