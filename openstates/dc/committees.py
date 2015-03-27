from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import re


class DCCommitteeScraper(CommitteeScraper):
    jurisdiction = 'dc'

    def scrape(self, term, chambers):
        # com_url = 'http://www.dccouncil.washington.dc.us/committees'
        com_url = 'http://dccouncil.us/committees'
        data = self.get(com_url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(com_url)

        #dc spelled committe(e) two different ways
        #IN THEIR HTML CLASS NAMES!
        comms = doc.xpath('//li[contains(@class,"node_committee-on")]/a')
        comms += doc.xpath('//li[contains(@class,"node_committe-on")]/a')
        for committee in comms:
            url = committee.attrib['href']
            comm_name = committee.text_content().strip()
            comm_data = self.get(url).text
            comm_page = lxml.html.fromstring(comm_data)
            comm_page.make_links_absolute(url)
            comm = Committee("upper",comm_name)

            chair = comm_page.xpath("//h3[text()='Committee Chair']/following-sibling::p")
            chair_name = chair[0].text_content().strip()
            comm.add_member(chair_name,role="chair")

            members = comm_page.xpath("//h3[text()='Councilmembers']/following-sibling::ul")
            members = members[0].xpath("./li")
            for m in members:
                mem_name = m.text_content().strip()
                if mem_name != chair_name:
                    comm.add_member(mem_name)

            comm.add_source(url)
            self.save_committee(comm)
