import re

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class KYCommitteeScraper(CommitteeScraper):
    jurisdiction = 'ky'
    latest_only = True

    def scrape(self, chamber, term):

        if chamber == 'upper':
            urls = ["http://www.lrc.ky.gov/committee/standing_senate.htm"]
            # also invoke joint scraper
            self.scrape('joint', term)
        elif chamber == 'lower':
            urls = ["http://www.lrc.ky.gov/committee/standing_house.htm"]
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
                self.scrape_committee(chamber, link)
                

    def scrape_committee(self, chamber, link, parent_comm=None):
        home_link = link.attrib["href"]
        name = re.sub(r'\s+\((H|S)\)$', '', link.text).strip().title()
        name = name.replace(".", "").strip()
        if "Subcommittee " in name:
            subcomm = name.split("Subcommittee")[1]
            subcomm = subcomm.replace(" on ","").replace(" On ", "")
            subcomm = subcomm.strip()
            comm = Committee(chamber, parent_comm, subcomm)
        else:
            for c in ["Committee", "Comm", "Sub","Subcommittee"]:
                if name.endswith(c):
                    name = name[:-1*len(c)].strip()
            comm = Committee(chamber, name)
        comm.add_source(home_link)
        comm_url = home_link.replace(
            'home.htm', 'members.htm')
        self.scrape_members(comm, comm_url)
        

        if comm['members']:
            self.save_committee(comm)
        else:
            self.logger.warning("Empty committee, skipping.")
        
        #deal with subcommittees
        if parent_comm is None:
            #checking parent_comm so we don't look for subcommittees
            #in subcommittees leaving us exposed to infinity 
            page = self.get(home_link).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(home_link)
            sub_links = page.xpath("//li/a[contains(@href, '/home.htm')]")
            for l in sub_links:
                if "committee" in l.text.lower():
                    self.scrape_committee(chamber, l, name)




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
