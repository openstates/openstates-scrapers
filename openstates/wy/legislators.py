
from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
class WYLegislatorScraper(LegislatorScraper):
    state = 'wy'

    def scrape(self, chamber, term):
        print chamber
        print term
