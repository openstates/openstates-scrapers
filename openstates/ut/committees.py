import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class UTCommitteeScraper(CommitteeScraper):
    jurisdiction = 'ut'

    def lxmlize(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page


    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        chamber_abbr = {'upper': 's', 'lower': 'h'}[chamber]

        url = "http://le.utah.gov/asp/interim/standing.asp?house=%s" % chamber_abbr
        page = self.lxmlize(url)

        for comm_link in page.xpath("//a[contains(@href, 'Com=')]"):
            comm_name = comm_link.text.strip()

            # Drop leading "House" or "Senate" from name
            comm_name = re.sub(r"^(House|Senate) ", "", comm_name)
            comm = Committee(chamber, comm_name)

            committee_page = self.lxmlize(comm_link.attrib['href'])

            for mbr_link in committee_page.xpath(
                    "//table[@class='memberstable']//a"):

                name = mbr_link.text.strip()
                role = mbr_link.tail.strip().strip(",").strip()
                type = "member"
                if role:
                    type = role

                comm.add_member(name, type)

            comm.add_source(url)
            comm.add_source(comm_link.get('href'))

            self.save_committee(comm)
