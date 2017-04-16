from pupa.scrape import Scraper, Organization
import lxml.html


class DCCommitteeScraper(Scraper):

    def scrape(self):
        com_url = 'http://dccouncil.us/committees'
        data = self.get(com_url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(com_url)

        # dc spelled committe(e) two different ways
        # IN THEIR HTML CLASS NAMES!
        comms = doc.xpath('//li[contains(@class,"node_committee-on")]/a')
        comms += doc.xpath('//li[contains(@class,"node_committe-on")]/a')
        for committee in comms:
            url = committee.attrib['href']
            name = committee.text_content().strip()
            comm_data = self.get(url).text
            comm_page = lxml.html.fromstring(comm_data)
            comm_page.make_links_absolute(url)

            # classify these as belonging to the legislature
            committee = Organization(name=name, classification='committee',
                                     chamber='legislature')

            chair = comm_page.xpath("//h3[text()='Committee Chair']/following-sibling::p")
            chair_name = chair[0].text_content().strip()
            committee.add_member(chair_name, role="chair")

            members = comm_page.xpath("//h3[text()='Councilmembers']/following-sibling::ul")
            members = members[0].xpath("./li")

            for m in members:
                mem_name = m.text_content().strip()
                if mem_name != chair_name:
                    committee.add_member(mem_name)

            committee.add_source(url)

            if not committee._related:
                self.warning('empty committee: %s;', name)
            else:
                yield committee
