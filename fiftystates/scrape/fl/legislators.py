import re

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class FLLegislatorScraper(LegislatorScraper):
    state = 'fl'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            self.scrape_senators(term)
        else:
            self.scrape_reps(term)

    def scrape_senators(self, term):
        url = ("http://www.flsenate.gov/Legislators/"
               "index.cfm?Mode=Member%20Pages&Submenu=1&Tab=legislators")

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for link in page.xpath("//a[contains(@href, '/legislators')]"):
                name = re.sub(r"\s+", " ", link.text).strip()

                # Special case - name_tools gets confused
                # by 'JD', thinking it is a suffix instead of a first name
                if name == 'Alexander, JD':
                    name = 'JD Alexander'
                elif name == 'Vacant':
                    name = 'Vacant Seat'

                district = link.xpath('string(../../td[2])').strip()
                party = link.xpath('string(../../td[3])').strip()

                leg = Legislator(term, 'upper', district, name,
                                 party=party)
                leg.add_source(url)
                self.save_legislator(leg)

    def scrape_reps(self, term):
        url = ("http://www.flhouse.gov/Sections/Representatives/"
               "representatives.aspx")

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page.decode('utf8'))

            for link in page.xpath("//a[contains(@href, 'MemberId')]"):
                name = re.sub(r"\s+", " ", link.text).strip()

                party = link.xpath('string(../../td[3])').strip()
                if party == 'D':
                    party = 'Democrat'
                elif party == 'R':
                    party = 'Republican'

                district = link.xpath('string(../../td[4])').strip()

                leg = Legislator(term, 'lower', district, name,
                                 party=party)
                leg.add_source(url)
                self.save_legislator(leg)
