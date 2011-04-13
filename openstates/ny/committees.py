import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


def parse_name(name):
    """
    Split a committee membership string into name and role.

    >>> parse_name('Felix Ortiz')
    ('Felix Ortiz', 'member')
    >>> parse_name('Felix Ortiz (Chair)')
    ('Felix Ortiz', 'chair')
    >>> parse_name('Felix Ortiz, Co-Chair')
    ('Felix Ortiz', 'co-chair')
    """
    name = re.sub(r'^Hon.\s+', '', name)

    roles = ["Chair", "Chairwoman", "Secretary", "Treasurer",
             "Parliamentarian", "Chaplain"]
    match = re.match(r'(.*),? \(?((Co|Vice)?-?\s*(%s))\)?' % '|'.join(roles),
                     name)
    if match:
        name = match.group(1).strip(' ,')
        role = match.group(2).lower()
        return (name, role)
    return (name, 'member')


class NYCommitteeScraper(CommitteeScraper):
    state = "ny"

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        if chamber == "upper":
            self.scrape_upper()
        elif chamber == "lower":
            self.scrape_lower()

    def scrape_lower(self):
        url = "http://assembly.state.ny.us/comm/"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'sec=mem')]"):
                name = link.xpath("string(../strong)").strip()
                if 'Caucus' in name:
                    continue

                url = link.attrib['href']

                self.scrape_lower_committee(name, url)

    def scrape_lower_committee(self, name, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            comm = Committee('lower', name)
            comm.add_source(url)

            for link in page.xpath("//a[contains(@href, 'mem?ad')]"):
                member = link.text.strip()
                member = re.sub(r'\s+', ' ', member)

                name, role = parse_name(member)
                comm.add_member(name, role)

            self.save_committee(comm)

    def scrape_upper(self):
        url = "http://www.nysenate.gov/committees"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, '/committee/')]"):
                name = link.text.strip()
                self.scrape_upper_committee(name, link.attrib['href'])

    def scrape_upper_committee(self, name, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            comm = Committee('upper', name)
            comm.add_source(url)

            member_div = page.xpath("//div[@class = 'committee-members']")[0]

            seen = set()
            for link in member_div.xpath(".//a"):
                if not link.text:
                    continue

                member = link.text.strip()
                member = re.sub(r'\s+', ' ', member)

                if member in seen or not member:
                    continue
                seen.add(member)

                name, role = parse_name(member)
                comm.add_member(name, role)

            self.save_committee(comm)
