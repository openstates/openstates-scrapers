import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin

import lxml.html


class UTCommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = 'ut'

    def scrape(self, term, chambers):
        self.validate_term(term, latest_only=True)

        url = "http://le.utah.gov/asp/interim/Main.asp?ComType=All&Year=2015&List=2#Results"
        page = self.lxmlize(url)

        for comm_link in page.xpath("//a[contains(@href, 'Com=')]"):
            comm_name = comm_link.text.strip()

            if "House" in comm_name:
                chamber = "lower"
            elif "Senate" in comm_name:
                chamber = "upper"
            else:
                chamber = "joint"


            # Drop leading "House" or "Senate" from name
            comm_name = re.sub(r"^(House|Senate) ", "", comm_name)
            comm = Committee(chamber, comm_name)

            committee_page = self.lxmlize(comm_link.attrib['href'])

            for mbr_link in committee_page.xpath(
                    "//table[@class='memberstable']//a"):

                name = mbr_link.text.strip()
                name = re.sub(r' \([A-Z]\)$', "", name)
                name = re.sub(r'^Sen. ', "", name)
                name = re.sub(r'^Rep. ', "", name)

                role = mbr_link.tail.strip().strip(",").strip()
                type = "member"
                if role:
                    type = role

                comm.add_member(name, type)

            comm.add_source(url)
            comm.add_source(comm_link.get('href'))

            self.save_committee(comm)
