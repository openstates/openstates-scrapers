import re

from pupa.scrape import Scraper, Organization
from openstates.utils import LXMLMixin

import lxml.html


class UTCommitteeScraper(Scraper):

    def scrape(self, chamber=None):

        url = "http://le.utah.gov/asp/interim/Main.asp?ComType=All&Year=2015&List=2#Results"
        html = self.get(url)
        page = lxml.html.fromstring(html)

        for comm_link in page.xpath("//a[contains(@href, 'Com=')]"):
            comm_name = comm_link.text.strip()

            chamber_type = ""
            if chamber:
                if "House" in comm_name:
                    chamber_type = "lower"
                elif "Senate" in comm_name:
                    chamber_type = "upper"
                else:
                    chamber_type = "joint"
            else:
                chamber_type = "joint" #chamber defaults to joint
            chamber = chamber_type

            # Drop leading "House" or "Senate" from name
            comm_name = re.sub(r"^(House|Senate) ", "", comm_name)
            committee = Organization(
                name,
                chamber=chamber,  # 'upper' or 'lower' (or joint)
                classification='committee'
            )

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

            yield comm
