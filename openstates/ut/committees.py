import re

from pupa.scrape import Scraper, Organization
from openstates.utils import LXMLMixin

import lxml.html


class UTCommitteeScraper(Scraper):

    def scrape(self, chamber=None):

        url = "http://le.utah.gov/asp/interim/Main.asp?ComType=All&Year=2015&List=2#Results"
        html = self.get(url)
        page = lxml.html.fromstring(html.text)

        for comm_link in page.xpath("//a[contains(@href, 'Com=')]"):
            name = comm_link.text.strip()

            chamber_type = ""
            if chamber:
                if "House" in name:
                    chamber_type = "lower"
                elif "Senate" in name:
                    chamber_type = "upper"
                else:
                    chamber_type = "joint"
            else:
                chamber_type = "joint" #chamber defaults to joint
            chamber = chamber_type

            # Drop leading "House" or "Senate" from name
            name = re.sub(r"^(House|Senate) ", "", name)

            committee = Organization(
                name,
                chamber=chamber,  # 'upper' or 'lower' (or joint)
                classification='committee'
            )

            committee_page = lxml.html.fromstring(comm_link.attrib['href'])

            for mbr_link in committee_page.xpath(
                    "//table[@class='memberstable']//a"):

                m_name = mbr_link.text.strip()
                m_name = re.sub(r' \([A-Z]\)$', "", m_name)
                m_name = re.sub(r'^Sen. ', "", m_name)
                m_name = re.sub(r'^Rep. ', "", m_name)

                role = mbr_link.tail.strip().strip(",").strip()
                type = "member"
                if role:
                    type = role

                committee.add_member(m_name, type)

            committee.add_source(url)
            committee.add_source(comm_link.get('href'))

            yield committee
