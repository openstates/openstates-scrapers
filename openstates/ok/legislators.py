import os
import csv

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
