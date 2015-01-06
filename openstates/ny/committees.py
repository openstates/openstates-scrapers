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
    jurisdiction = "ny"
    latest_only = True

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber)()

    def scrape_lower(self, only_names=None):
        committees = []
        url = "http://assembly.state.ny.us/comm/"
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'sec=mem')]"):
            name = link.xpath("string(../strong)").strip()
            if 'Caucus' in name:
                continue

            url = link.attrib['href']

            committees.append(name)

            self.scrape_lower_committee(name, url)
        return committees

    def scrape_lower_committee(self, name, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)

        comm = Committee('lower', name)
        comm.add_source(url)
        seen = set()
        for link in page.xpath("//div[@class='commlinks']//a[contains(@href, 'mem')]"):

            member = link.text.strip()
            member = re.sub(r'\s+', ' ', member)

            name, role = parse_name(member)

            # Figure out if this person is the chair.
            role_type = link.xpath('../../preceding-sibling::div[1]/text()')
            if role_type in (['Chair'], ['Co-Chair']):
                role = 'chair'
            else:
                role = 'member'

            if name not in seen:
                comm.add_member(name, role)
                seen.add(name)

        if comm['members']:
            self.save_committee(comm)

    def scrape_upper(self):
        committees = []
        url = "http://www.nysenate.gov/committees"
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for h2 in page.xpath("//h2"):
            committee_types = [
                'Standing Committees',
                'Temporary Committees',
                'Task Forces & Other Entities'
            ]

            if h2.text not in committee_types:
                continue

            for link in h2.getparent().xpath(".//a[contains(@href, '/committee/')]"):
                name = link.text.strip()

                committees.append(name)
                self.scrape_upper_committee(name, link.attrib['href'])

        return committees

    def scrape_upper_committee(self, name, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)

        comm = Committee('upper', name)
        comm.add_source(url)

        member_div = page.xpath("//div[@class = 'committee-members']")[0]

        xpath = '//label[contains(., "Chair:")]/following-sibling::a/text()'
        chair = page.xpath(xpath)
        if chair:
            comm.add_member(chair.pop().strip(), 'chair')

        seen = set([member['name'] for member in comm['members']])
        for link in member_div.xpath(".//a"):
            if not link.text:
                try:
                    # On one vice chair, the text was nested differently.
                    member = link[0].tail.strip()
                except (IndexError, AttributeError):
                    continue
            else:
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

        if comm['members']:
            self.save_committee(comm)
