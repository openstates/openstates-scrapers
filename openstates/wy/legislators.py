
from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
class WYLegislatorScraper(LegislatorScraper):
    state = 'wy'

    def scrape(self, chamber, term):
        years = []
        for t in self.metadata['terms']:
            if term == t['name']:
                years.append(t['start_year'])
                years.append(t['end_year'])
                break
        print chamber
        print term
        print years
