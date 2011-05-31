import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class OKLegislatorScraper(LegislatorScraper):
    state = 'ok'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        if chamber == 'lower':
            self.scrape_lower(term)
        else:
            self.scrape_upper(term)

    def scrape_lower(self, term):
        url = "http://www.okhouse.gov/Members/Default.aspx"
        page = lxml.html.fromstring(self.urlopen(url))

        for link in page.xpath("//a[contains(@href, 'District')]")[3:]:
            name = link.text.strip()
            district = link.xpath("string(../../td[3])").strip()

            party = link.xpath("string(../../td[4])").strip()
            if party == 'R':
                party = 'Republican'
            elif party == 'D':
                party = 'Democratic'

            leg = Legislator(term, 'lower', district, name, party=party)
            leg.add_source(url)
            self.save_legislator(leg)

    def scrape_upper(self, term):
        url = "http://oksenate.gov/Senators/Default.aspx?selectedtab=0"
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        table = page.xpath("//table[contains(@summary, 'alphabetically')]")[0]

        for link in table.xpath(".//a[contains(@href, '_bio.aspx')]")[2:]:
            name = link.text.strip()
            name = re.sub(r'\s+', ' ', name)
            if not name:
                continue

            match = re.match(r'([^\(]+)\s+\(([RD])\)', name)
            name = match.group(1)
            party = match.group(2)

            if party == 'R':
                party = 'Republican'
            elif party == 'D':
                party = 'Democratic'

            district = link.xpath("string(../../span[2])").strip()
            if not district:
                district = link.xpath("..")[0].tail.strip()

            leg = Legislator(term, 'upper', district, name, party=party)
            leg.add_source(url)
            self.save_legislator(leg)
