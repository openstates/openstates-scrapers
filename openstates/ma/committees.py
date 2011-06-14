from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

import re

class MACommitteeScraper(CommitteeScraper):
    state = 'ma'

    def scrape(self, chamber, term):
        if chamber == 'upper':
            page_types = ['Senate', 'Joint']
        elif chamber == 'lower':
            page_types = ['House']

        foundComms = []

        for page_type in page_types:
            url = 'http://www.malegislature.gov/Committees/' + page_type

            with self.urlopen(url) as html:
                doc = lxml.html.fromstring(html)
                doc.make_links_absolute('http://www.malegislature.gov')

                for com_url in doc.xpath('//div[@class="widgetContent"]/ul/li/a/@href'):
                    self.scrape_committee(chamber, com_url)

    def scrape_committee(self, chamber, url):
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            name = doc.xpath('//h3/text()')[0]
            com = Committee(chamber, name)
            com.add_source(url)

            for describe_div in doc.xpath('//div[@class="describe"]'):
                role = describe_div.xpath('.//b/text()')[-1]
                name = describe_div.xpath('.//u/a/text()')[0]
                com.add_member(name, role)

            for member in doc.xpath('//div[@class="membersGallyList"]/ul/li/a/text()'):
                com.add_member(name)

            self.save_committee(com)
