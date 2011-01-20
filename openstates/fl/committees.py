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
            self.scrape_upper_committees(term)

    def scrape_upper_committees(self, term):
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
                    comm_name, sub_name = comm_name.split('Subcommittee on')
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
