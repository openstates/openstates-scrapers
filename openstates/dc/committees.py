from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import re


class DCCommitteeScraper(CommitteeScraper):
    jurisdiction = 'dc'

    def scrape(self, term, chambers):
        # com_url = 'http://www.dccouncil.washington.dc.us/committees'
        com_url = 'http://dccouncil.us/committees'
        data = self.urlopen(com_url)
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(com_url)

        urls = set(doc.xpath('//a[contains(@href, "committee-on")]/@href'))
        for url in urls:
            data = self.urlopen(url)
            doc = lxml.html.fromstring(data)

            try:
                name = doc.xpath('//h1/text()')[0].replace('Committee on ', '')
            except IndexError:
                name = doc.xpath('//h2/text()')[0].replace('Committee on ', '')


            # skip link to Committees page
            if name == 'Committees':
                continue

            com = Committee('upper', name)

            chairs = []

            for chair in doc.xpath('//h3[text()="Committee Chair"]/following-sibling::p'):
                com.add_member(chair.text_content(), role='chairperson')
                chairs.append(chair.text_content())

            for member in doc.xpath('//h3[text()="Councilmembers"]/following-sibling::ul//a'):
                if member.text_content() not in chairs:
                    com.add_member(member.text_content(), role='member')

            com.add_source(url)
            self.save_committee(com)
