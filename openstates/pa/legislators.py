import re
import itertools

from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import legislators_url

import lxml.html


class PALegislatorScraper(LegislatorScraper):
    jurisdiction = 'pa'

    def scrape(self, chamber, term):
        # Pennsylvania doesn't make member lists easily available
        # for previous sessions, unfortunately
        self.validate_term(term, latest_only=True)

        leg_list_url = legislators_url(chamber)

        with self.urlopen(leg_list_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(leg_list_url)

            for link in page.xpath("//a[contains(@href, '_bio.cfm')]"):
                full_name = link.text
                district = link.getparent().getnext().tail.strip()
                district = re.search("District (\d+)", district).group(1)

                party = link.getparent().tail.strip()[-2]
                if party == 'R':
                    party = 'Republican'
                elif party == 'D':
                    party = 'Democratic'

                url = link.get('href')

                legislator = Legislator(term, chamber, district,
                                        full_name, party=party, url=url)
                legislator.add_source(leg_list_url)

                # Scrape email, offices, photo.
                page = self.urlopen(url)
                doc = lxml.html.fromstring(page)
                doc.make_links_absolute(url)

                self.scrape_email_address(url, page, legislator)
                self.scrape_offices(url, doc, legislator)
                self.save_legislator(legislator)

    def scrape_email_address(self, url, page, legislator):
        if re.search(r'var \S+\s+= "(\S+)";', page):
            vals = re.findall(r'var \S+\s+= "(\S+)";', page)
            legislator['email'] = '%s@%s%s' % tuple(vals)

    def scrape_offices(self, url, doc, legislator):
        el = doc.xpath('//h4[contains(., "Contact")]/..')[0]
        for office in Offices(el, self):
            legislator.add_office(**office)
        legislator.add_source(url)


class Offices(object):
    '''Terrible. That's what PA's offices are.
    '''

    class ParseError(Exception):
        pass

    def __init__(self, el, scraper):
        self.el = el
        self.scraper = scraper
        lines = list(el.itertext())[5:]
        lines = [x.strip() for x in lines]
        lines = filter(None, lines)
        self.lines = lines

    def __iter__(self):
        try:
            for lines in self.offices_lines():
                yield Office(lines).parsed()
        except self.ParseError:
            self.scraper.logger.warning("Couldn't parse offices.")
            return

    def break_at(self):
        '''The first line of the address, usually his/her name.'''
        lines = self.lines[::-1]

        # The legr's full name is the first line in each address.
        junk = set('contact district capitol information'.split())
        while True:
            try:
                break_at = lines.pop()
            except IndexError:
                raise self.ParseError

            # Skip lines that are like "Contact" instead of
            # the legislator's full name.
            if junk & set(break_at.lower().split()):
                continue
            else:
                break
        return break_at

    def offices_lines(self):
        office = []
        lines = self.lines
        break_at = self.break_at()
        while lines and True:
            line = lines.pop()
            if line == break_at:
                yield office
                office = []
            else:
                office.append(re.sub(r'\s+', ' ', line))


class Office(object):
    '''They're really quite bad.'''

    re_phone = re.compile(r' \d{3}\-\d{4}')
    re_fax = re.compile(r'^\s*fax:\s*', re.I)

    def __init__(self, lines):
        junk = ['Capitol', 'District']
        self.lines = [x for x in lines if x not in junk]

    def phone(self):
        '''Return the first thing that looks like a phone number.'''
        lines = filter(self.re_phone.search, self.lines)
        for line in lines:
            if not line.strip().lower().startswith('fax:'):
                return line.strip()

    def fax(self):
        lines = filter(self.re_fax.search, self.lines)
        if lines:
            return self.re_fax.sub('', lines.pop()) or None

    def type_(self):
        for line in self.lines:
            if 'capitol' in line.lower():
                return 'capitol'
            elif 'east wing' in line.lower():
                return 'capitol'
        return 'district'

    def name(self):
        return self.type_().title() + ' Office'

    def address(self):
        lines = itertools.ifilterfalse(self.re_phone.search, self.lines)
        lines = itertools.ifilterfalse(self.re_fax.search, lines)
        lines = list(lines)
        for i, line in enumerate(lines):
            if re.search('PA \d{5}', line):
                break

        # If address lines are backwards, fix.
        if i <= 2:
            lines = lines[::-1]

        # Make extra sure "PA 12345" line is last.
        while not re.search('PA \d{5}', lines[-1]):
            lines = lines[-1:] + lines[:-1]
        address = '\n'.join(lines)
        return address

    def parsed(self):
        return dict(
            phone=self.phone(),
            fax=self.fax(),
            address=self.address(),
            type=self.type_(),
            name=self.name())
