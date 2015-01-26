import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class KYCommitteeScraper(CommitteeScraper):
    jurisdiction = 'ky'
    latest_only = True

    def scrape(self, chamber, term):

        if chamber == 'upper':
            url = "http://www.lrc.ky.gov/committee/standing_senate.htm"
            # also invoke joint scraper
            self.scrape('joint', term)
        elif chamber == 'lower':
            url = "http://www.lrc.ky.gov/committee/standing_house.htm"
        else:
            url = "http://www.lrc.ky.gov/committee/interim.htm"
            chamber = 'joint'

        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        links = []

        cttypages = [
            "//a[contains(@href, 'standing/')]",
            "//a[contains(@href, 'interim')]"
        ]

        for exp in cttypages:
            linkz = page.xpath(exp)
            links = links + linkz

        for link in links:
            name = re.sub(r'\s+\((H|S)\)$', '', link.text).strip().title()
            comm = Committee(chamber, name)
            comm_url = link.attrib['href'].replace(
                'home.htm', 'members.htm')
            self.scrape_members(comm, comm_url)
            if comm['members']:
                self.save_committee(comm)

    def scrape_members(self, comm, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        comm.add_source(url)

        for link in page.xpath("//a[contains(@href, 'Legislator')]"):
            name = re.sub(r'^(Rep\.|Sen\.) ', '', link.text).strip()
            if not link.tail or not link.tail.strip():
                role = 'member'
            elif link.tail.strip() == '[Chair]':
                role = 'chair'
            elif link.tail.strip() == '[Co-Chair]':
                role = 'co-chair'
            elif link.tail.strip() == '[Vice Chair]':
                role = 'vice chair'
            else:
                raise Exception("unexpected position: %s" % link.tail)
            comm.add_member(name, role=role)
