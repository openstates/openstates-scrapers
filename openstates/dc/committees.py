from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import re


class DCCommitteeScraper(CommitteeScraper):
    state = 'dc'

    def scrape(self, chamber, term):
        # do nothing if they're trying to get a lower chamber
        if chamber == 'lower':
            return

        com_url = 'http://www.dccouncil.washington.dc.us/committees'
        data = self.urlopen(com_url)
        doc = lxml.html.fromstring(data)

        urls = set(doc.xpath('//a[contains(@href, "committee-on")]/@href'))
        for url in urls:
            data = self.urlopen(url)
            doc = lxml.html.fromstring(data)

            name = doc.xpath('//h1/text()')[0].replace('Committee on ', '')
            com = Committee('upper', name)

            for chair in doc.xpath('//h3[text()="Committee Chair"]/following-sibling::p'):
                com.add_member(chair.text_content(), role='chairperson')

            for member in doc.xpath('//h3[text()="Councilmembers"]/following-sibling::p/a'):
                com.add_member(member.text_content(), role='member')

            com.add_source(url)
            self.save_committee(com)
