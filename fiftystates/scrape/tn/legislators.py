from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html

class TNLegislatorScraper(LegislatorScraper):
    state = 'tn'

    def scrape(self, chamber, term):
        print chamber
        print term

