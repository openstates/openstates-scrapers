import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class FLCommitteeScraper(CommitteeScraper):
    state = 'fl'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            self.scrape_upper_committees()
        else:
            self.scrape_lower_committees()

    def scrape_upper_committees(self):
        url = ("http://www.flsenate.gov/Committees/"
               "index.cfm?Mode=Committee%20Pages&Submenu=1&Tab=committees")
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            path = "//a[contains(@href, 'Directory=committees')]"
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
                self.save_committee(comm)

    def scrape_upper_committee(self, comm, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            comm.add_source(url)

            path = "//a[contains(@href, 'legislators')]/name"
            for name in page.xpath(path):
                b = name.xpath("../preceding-sibling::b")
                if b:
                    mtype = b[0].text.strip(': \r\n\t').lower()
                else:
                    mtype = 'member'

                comm.add_member(name.text.strip(), mtype)

    def scrape_lower_committees(self):
        url = ("http://www.myfloridahouse.gov/Sections/Committees/"
               "committees.aspx")
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'CommitteeId')]"):
                comm_name = link.text.strip()

                if comm_name.startswith('Joint'):
                    continue

                if comm_name.endswith('Committee'):
                    parent = re.sub(r'Committee$', '', comm_name).strip()
                    sub = None
                else:
                    sub = re.sub(r'Subcommittee$', '', comm_name).strip()

                comm = Committee('lower', parent, sub)
                self.scrape_lower_committee(comm, link.attrib['href'])
                self.save_committee(comm)

    def scrape_lower_committee(self, comm, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            comm.add_source(url)

            for link in page.xpath("//a[contains(@href, 'MemberId')]"):
                name = re.sub(r' \([A-Z]\)$', '', link.text).strip()

                mtype = link.xpath(
                    "string(../following-sibling::td)").strip().lower()
                if not mtype:
                    mtype = 'member'

                comm.add_member(name, mtype)
