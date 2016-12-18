from billy.scrape.legislators import LegislatorScraper

from .v1 import COLegislatorScraper as COLegislatorV1Scraper
from .v2 import COLegislatorScraper as COLegislatorV2Scraper


class COLegislatorScraper(LegislatorScraper):
    """Scraper capabable of scraping the different iterations of the Colorado legislature site"""
    jurisdiction = 'co'

    def __init__(self, *args, **kwargs):
        super(COLegislatorScraper, self).__init__(*args, **kwargs)
        self.v1_scraper = COLegislatorV1Scraper(*args, **kwargs)
        self.v2_scraper = COLegislatorV2Scraper(*args, **kwargs)

    def scrape(self, chamber, term):
        if term == '2015-2016':
            self.v2_scraper.scrape(chamber, term)
            # XXX: Hackily copy the output_names of the actual scraper to this
            # wrapper one.
            self.output_names = self.v2_scraper.output_names
        else:
            self.v1_scraper.scrape(chamber, term)
            self.output_names = self.v1_scraper.output_names
