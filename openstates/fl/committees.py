import re
from itertools import chain

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class FLCommitteeScraper(CommitteeScraper):
    jurisdiction = 'fl'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            self.scrape_upper_committees()
        else:
            self.scrape_lower_committees()

    def scrape_upper_committees(self):
        url = "http://flsenate.gov/Committees/"
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        path = "//a[contains(@href, 'Committees/Show')]"
        for link in page.xpath(path):
            comm_name = link.text.strip()

            if comm_name.startswith('Joint'):
                continue

            if 'Subcommittee on' in comm_name:
                comm_name, sub_name = comm_name.split(' Subcommittee on ')
            else:
                comm_name, sub_name = comm_name, None

            comm = Committee('upper', comm_name, sub_name)
            self.scrape_upper_committee(comm, link.attrib['href'])
            if comm['members']:
                self.save_committee(comm)

    def scrape_upper_committee(self, comm, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        comm.add_source(url)

        path = "//a[contains(@href, 'Senators')]/name"
        seen = set()
        for name in page.xpath(path):
            dt = name.xpath("../../preceding-sibling::dt")
            if dt:
                mtype = dt[0].text.strip(': \r\n\t').lower()
            else:
                mtype = 'member'

            member = re.sub(r'\s+', ' ', name.text.strip())
            if (member, mtype) not in seen:
                comm.add_member(member, mtype)
                seen.add((member, mtype))

    def scrape_lower_committees(self):
        url = ("http://www.myfloridahouse.gov/Sections/Committees/"
               "committees.aspx")
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'CommitteeId')]"):
            comm_name = link.text.strip()

            if 'Committee' in comm_name:
                parent = re.sub(r'Committee$', '', comm_name).strip()
                sub = None
            else:
                sub = re.sub(r'Subcommittee$', '', comm_name).strip()

            comm = Committee('lower', parent, sub)
            self.scrape_lower_committee(comm, link.get('href'))
            if comm['members']:
                self.save_committee(comm)

        for link in page.xpath('//a[contains(@href, "committees/joint")]/@href'):
            self.scrape_joint_committee(link)

    def scrape_joint_committee(self, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        name = doc.xpath('//h1/text()') or doc.xpath('//h2/text()')
        name = name[0].strip()

        comm = Committee('joint', name)
        comm.add_source(url)

        members = chain(doc.xpath('//a[contains(@href, "MemberId")]'),
                        doc.xpath('//a[contains(@href, "Senators")]'))

        seen = set()
        for a in members:
            parent_content = a.getparent().text_content()
            if ':' in parent_content:
                title = parent_content.split(':')[0].strip()
            else:
                title = 'member'

            name = a.text.split(' (')[0].strip()
            if (name, title) not in seen:
                comm.add_member(name, title)
                seen.add((name, title))

        if comm['members']:
            self.save_committee(comm)

    def scrape_lower_committee(self, comm, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        comm.add_source(url)

        for link in page.xpath("//p[@class='committeelinks']/a[contains(@href, 'MemberId')]"):
            # strip off spaces and everything in [R/D]
            name = link.text.strip().split(' [')[0]
            # membership type span follows link
            mtype = link.getnext().text_content().strip()
            if not mtype:
                mtype = 'member'

            comm.add_member(name, mtype)
