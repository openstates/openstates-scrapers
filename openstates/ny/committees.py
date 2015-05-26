import re

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

    role = "member"
    if match:
        name = match.group(1).strip(' ,')
        role = match.group(2).lower()


    name = name.replace("Sen.","").replace("Rep.","").strip()


    return (name, role)


class NYCommitteeScraper(CommitteeScraper):
    jurisdiction = "ny"
    latest_only = True

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber)()

    def scrape_lower(self, only_names=None):
        committees = []
        url = "http://assembly.state.ny.us/comm/"
        page = self.get(url).text
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
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        comm = Committee('lower', name)
        comm.add_source(url)
        seen = set()
        for link in page.xpath("//div[@class='commlinks']//a[contains(@href, 'mem')]"):

            member = link.text.strip()
            member = re.sub(r'\s+', ' ', member)

            name, role = parse_name(member)
            if name is None:
                continue

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
        page = self.get(url).text
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
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        comm = Committee('upper', name)
        comm.add_source(url)

        chair_div = page.xpath("//div[@class = 'committee-chair']")
        for chair in chair_div:
            role = chair.xpath("./label/text()")[0].replace(":","").strip().lower()

            # Remove title and arbitrary whitespace from names
            member_name = chair.xpath(".//a[not(@class)]/text()")[-2].strip()
            member_name = re.sub(r'^Sen\.', "", member_name).strip()
            member_name = " ".join(member.split())

            comm.add_member(member_name, role)

        member_list = page.xpath("//div[@class='committee-members']//ul/li/div/span/a/text()")
        for member in member_list:
            member_name = " ".join(member.split())
            comm.add_member(member_name, "member")

        if comm['members']:
            self.save_committee(comm)
