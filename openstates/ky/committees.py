import re

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class KYCommitteeScraper(CommitteeScraper):
    jurisdiction = 'ky'
    latest_only = True

    def scrape(self, chamber, term):

        if chamber == 'upper':
            urls = ["http://www.lrc.ky.gov/committee/standing_senate.htm",
                    "http://www.lrc.ky.gov/committee/standing/A&R(S)/home.htm"]
            # also invoke joint scraper
            self.scrape('joint', term)
        elif chamber == 'lower':
            urls = ["http://www.lrc.ky.gov/committee/standing_house.htm",
                    "http://www.lrc.ky.gov/committee/standing/A&R(H)/home.htm"]
        else:
            urls = ["http://www.lrc.ky.gov/committee/interim.htm",
                    "http://www.lrc.ky.gov/committee/statutory.htm"]

            chamber = 'joint'

        for url in urls:
            page = self.get(url).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            links = []

            cttypages = [
                "//a[contains(@href, 'standing/')]",
                "//a[contains(@href, 'interim')]",
                "//a[contains(@href, 'statutory')]"
            ]

            for exp in cttypages:
                linkz = page.xpath(exp)
                links = links + linkz

            for link in links:
                if "home" not in link.attrib["href"].lower():
                    #allows us to scrape known subcommittee
                    continue
                name = re.sub(r'\s+\((H|S)\)$', '', link.text).strip().title()
                name = name.replace(".", "")
                comm = Committee(chamber, name)
                comm_url = link.attrib['href'].replace(
                    'home.htm', 'members.htm')
                self.scrape_members(comm, comm_url)
                if comm['members']:
                    self.save_committee(comm)


    def scrape_members(self, comm, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        comm.add_source(url)

        for link in page.xpath("//a[contains(@href, 'Legislator')]"):
            name = re.sub(r'^(Rep\.|Sen\.) ', '', link.text).strip()
            name = name.replace("  ", " ")
            if not link.tail or not link.tail.strip():
                role = 'member'
            elif link.tail.strip() == '[Chair]':
                role = 'chair'
            elif link.tail.strip() == '[Co-Chair]':
                role = 'co-chair'
            elif link.tail.strip() == '[Vice Chair]':
                role = 'vice chair'
            elif link.tail.strip() in ['[ex officio]', '[non voting ex officio]', '[Liaison Member]']:
                role = 'member'
            else:
                raise Exception("unexpected position: %s" % link.tail)
            comm.add_member(name, role=role)
