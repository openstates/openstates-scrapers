from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.committees import CommitteeScraper, Committee

import lxml.html


class LACommitteeScraper(CommitteeScraper):
    state = 'md'

    def scrape(self, chamber, year):
        if year != '2009':
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_senate()
        else:
            self.scrape_house()

    def scrape_senate(self):
        url = 'http://senate.legis.state.la.us/Committees/default.asp'
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)
            page.make_links_absolute(url)

            links = page.xpath('//b[contains(text(), "Standing Committees")]'
                               '/../following-sibling::font/ul/li/a')

            for link in links:
                name = link.xpath('string()')
                url = link.attrib['href']

                self.scrape_senate_committee(name, url)

    def scrape_senate_committee(self, name, url):
        url = url.replace('Default.asp', 'Assignments.asp')

        committee = Committee('upper', name)
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)

            links = page.xpath('//table[@bordercolor="#EBEAEC"]/tr/td/font/a')

            for link in links:
                name = link.xpath('string()')
                name = name.replace('Senator ', '').strip()

                committee.add_member(name)

        self.save_committee(committee)
