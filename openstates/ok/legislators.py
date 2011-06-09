import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import xlrd
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
        url = "http://www.oksenate.gov/Senators/directory.xls"
        fname, resp = self.urlretrieve(url)

        sheet = xlrd.open_workbook(fname).sheet_by_index(0)

        for rownum in xrange(1, sheet.nrows):
            name = str(sheet.cell(rownum, 0).value)
            if not name:
                continue

            party = str(sheet.cell(rownum, 1).value)
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'
            elif not party:
                party = 'N/A'

            district = str(int(sheet.cell(rownum, 2).value))
            email = str(sheet.cell(rownum, 6).value)

            leg = Legislator(term, 'upper', district, name, party=party,
                             email_address=email)
            leg.add_source(url)
            self.save_legislator(leg)
