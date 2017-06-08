import re

from pupa.scrape import Scraper, Organization
from openstates.utils import LXMLMixin


class UTCommitteeScraper(Scraper, LXMLMixin):

    def scrape(self, chamber=None):
        url = "http://le.utah.gov/asp/interim/Main.asp?ComType=All&Year=2015&List=2#Results"
        page = self.lxmlize(url)

        for comm_link in page.xpath("//a[contains(@href, 'Com=')]"):
            comm_name = comm_link.text.strip()

            if "House" in comm_name:
                chamber = "lower"
            elif "Senate" in comm_name:
                chamber = "upper"
            else:
                chamber = "legislature"

            # Drop leading "House" or "Senate" from name
            comm_name = re.sub(r"^(House|Senate) ", "", comm_name)
            comm = Organization(name=comm_name, chamber=chamber,
                                classification='committee')
            committee_page = self.lxmlize(comm_link.attrib['href'])

            for mbr_link in committee_page.xpath(
                    "//table[@class='memberstable']//a"):

                name = mbr_link.text.strip()
                name = re.sub(r' \([A-Z]\)$', "", name)
                name = re.sub(r'^Sen. ', "", name)
                name = re.sub(r'^Rep. ', "", name)

                role = mbr_link.tail.strip().strip(",").strip()
                typ = "member"
                if role:
                    typ = role
                comm.add_member(name, typ)

            comm.add_source(url)
            comm.add_source(comm_link.get('href'))

            yield comm
