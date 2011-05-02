import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class KYCommitteeScraper(CommitteeScraper):
    state = 'ky'

    def scrape(self, chamber, term):
        if term != '2011':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            url = "http://www.lrc.ky.gov/org_adm/committe/standing_senate.htm"
        elif chamber == 'lower':
            url = "http://www.lrc.ky.gov/org_adm/committe/standing_house.htm"
        else:
            return

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'standing/')]"):
                name = re.sub(r'\s+\((H|S)\)$', '', link.text).strip()
                comm = Committee(chamber, name)
                comm_url = link.attrib['href'].replace(
                    'home.htm', 'members.htm')
                self.scrape_members(comm, comm_url)
                self.save_committee(comm)

    def scrape_members(self, comm, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            comm.add_source(url)

            for link in page.xpath("//a[contains(@href, 'Legislator')]"):
                name = re.sub(r'^(Rep\.|Sen\.) ', '', link.text).strip()
                comm.add_member(name)
