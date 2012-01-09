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
    >>> parse_name('Hon. Felix Ortiz, Co-Chair')
    ('Felix Ortiz', 'co-chair')
    >>> parse_name('Owen H.\\r\\nJohnson (Vice Chairperson)')
    ('Owen H. Johnson', 'vice chairperson')
    """
    name = re.sub(r'^(Hon\.|Assemblyman|Assemblywoman)\s+', '', name)
    name = re.sub(r'\s+', ' ', name)

    roles = ["Chairwoman", "Chairperson", "Chair", "Secretary", "Treasurer",
             "Parliamentarian", "Chaplain"]
    match = re.match(
        r'([^(]+),? \(?((Co|Vice)?-?\s*(%s))\)?' % '|'.join(roles),
        name)

    if match:
        name = match.group(1).strip(' ,')
        role = match.group(2).lower()
        return (name, role)
    return (name, 'member')


class NYCommitteeScraper(CommitteeScraper):
    state = "ny"
    latest_only = True

    def scrape(self, chamber, term):
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

                if name == 'New York State Conference of Black Senators':
                    # stop scraping once we reach the caucuses
                    break

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

                next_elem = link.getnext()
                if (next_elem is not None and
                    next_elem.tag == 'a' and
                    next_elem.attrib['href'] == link.attrib['href']):
                    # Sometimes NY is cool and splits names across a
                    # couple links
                    member = "%s %s" % (member, next_elem.text.strip())

                member = re.sub(r'\s+', ' ', member)

                if member in seen or not member:
                    continue
                seen.add(member)

                name, role = parse_name(member)
                comm.add_member(name, role)

            self.save_committee(comm)
