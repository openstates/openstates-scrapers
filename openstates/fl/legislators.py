import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

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
        url = "http://www.flsenate.gov/Senators/"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'Senators/s')]"):
                name = link.text.strip()
                name = re.sub(r'\s+', ' ', name)

                if name == 'Vacant':
                    continue

                # Special case - name_tools gets confused
                # by 'JD', thinking it is a suffix instead of a first name
                if name == 'Alexander, JD':
                    name = 'JD Alexander'
                elif name == 'Vacant':
                    name = 'Vacant Seat'

                district = link.xpath("string(../../td[1])")
                party = link.xpath("string(../../td[2])")

                photo_url = ("http://www.flsenate.gov/userContent/"
                             "Senators/2010-2012/photos/s%03d.jpg" % (
                                 int(district)))

                leg = Legislator(term, 'upper', district, name,
                                 party=party, photo_url=photo_url)
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
                    party = 'Democratic'
                elif party == 'R':
                    party = 'Republican'

                district = link.xpath('string(../../td[4])').strip()

                leg = Legislator(term, 'lower', district, name,
                                 party=party)
                leg.add_source(url)
                self.save_legislator(leg)
