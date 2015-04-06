import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class OKCommitteeScraper(CommitteeScraper):
    jurisdiction = "ok"
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == "upper":
            self.scrape_upper()
        elif chamber == "lower":
            self.scrape_lower()

    def scrape_lower(self):
        url = "http://www.okhouse.gov/Committees/Default.aspx"
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        parents = {}

        for link in page.xpath("//table[@id='ctl00_ContentPlaceHolder1_dgrdCommittee_ctl00']//a[contains(@href, 'Members')]"):
            name = link.xpath("string()").strip()

            if 'Members' in name or 'Conference' in name:
                continue

            match = re.search(r'CommID=(\d+)&SubCommID=(\d+)',
                              link.attrib['href'])
            comm_id, sub_comm_id = int(match.group(1)), int(match.group(2))

            if sub_comm_id == 0:
                parents[comm_id] = name
                parent = None
            else:
                parent = parents[comm_id]

            self.scrape_lower_committee(name, parent, link.attrib['href'])

    def scrape_lower_committee(self, name, parent, url):
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        if 'Joint' in name or (parent and 'Joint' in parent):
            chamber = 'joint'
        else:
            chamber = 'lower'

        if parent:
            comm = Committee(chamber, parent, subcommittee=name)
        else:
            comm = Committee(chamber, name)
        comm.add_source(url)

        xpath = "//a[contains(@href, 'District')]"
        for link in page.xpath(xpath):
            member = link.xpath('string()').strip()
            member = re.sub(r'\s+', ' ', member)

            if not member or member == 'House District Maps':
                continue

            match = re.match(r'((Co-)?(Vice )?Chair)?Rep\. ([^\(]+)', member)
            member = match.group(4).strip()
            role = match.group(1) or 'member'

            comm.add_member(member, role.lower())

        if not comm['members']:
            if comm['subcommittee'] == 'test':
                # Whoopsie, prod data.
                return

            raise Exception('no members for %s (%s)' % (
                comm['committee'], comm['subcommittee'])
            )

        self.save_committee(comm)

    def scrape_upper(self):
        url = "http://www.oksenate.gov/Committees/standingcommittees.htm"
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'standing/')]"):
            name = link.text.strip()
            name = re.sub(r'\s+', ' ', name)
            if 'Committee List' in name:
                continue

            self.scrape_upper_committee(name, link.attrib['href'])

    def scrape_upper_committee(self, name, url):
        page = lxml.html.fromstring(self.get(url).text)

        comm = Committee('upper', name)
        comm.add_source(url)

        for link in page.xpath("//a[contains(@href, 'biographies')]"):
            member = link.xpath("string()").strip()
            member = re.sub(r'\s+', ' ', member)
            if not member:
                continue
            role = link.tail
            if not role:
                role = 'member'
            elif 'Vice Chair' in role:
                role = 'vice chair'
            elif 'Chair' in role:
                role = 'chair'
            comm.add_member(member, role=role)

        if not comm['members']:
            raise Exception('no members for %s', comm['name'])
        self.save_committee(comm)
