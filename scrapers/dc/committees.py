from openstates.scrape import Scraper, Organization
import re
import lxml.html


class DCCommitteeScraper(Scraper):
    def remove_title(self, name):
        return (
            re.sub(r"(Ward \d+\s+)*Councilmember\s*", "", name)
            .replace("At-Large", "")
            .strip()
        )

    def scrape(self):
        com_url = "http://dccouncil.us/committees"
        data = self.get(com_url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(com_url)

        comms = set(doc.xpath('//a[contains(@href, "dccouncil.us/committees/")]'))

        for committee in comms:
            url = committee.attrib["href"]
            name = committee.text_content().strip()
            comm_data = self.get(url).text
            comm_page = lxml.html.fromstring(comm_data)
            comm_page.make_links_absolute(url)

            # classify these as belonging to the legislature
            committee = Organization(
                name=name, classification="committee", chamber="legislature"
            )

            if comm_page.xpath('//p[@class="page-summary"]'):
                summary = (
                    comm_page.xpath('//p[@class="page-summary"]')[0]
                    .text_content()
                    .strip()
                )
                committee.extras["summary"] = summary

            chair = comm_page.xpath("//h4[text()='Chairperson']/following-sibling::p")
            chair_name = chair[0].text_content().strip()
            chair_name = self.remove_title(chair_name)
            committee.add_member(chair_name, role="chair")

            members = comm_page.xpath(
                "//h4[text()='Councilmembers']/following-sibling::ul"
            )
            members = members[0].xpath("./li")

            for m in members:
                mem_name = m.text_content().strip()
                mem_name = self.remove_title(mem_name)
                if mem_name != chair_name:
                    committee.add_member(mem_name)

            committee.add_source(url)
            committee.add_link(url, note="Official Website")

            if not committee._related:
                self.warning("empty committee: %s;", name)
            else:
                yield committee
