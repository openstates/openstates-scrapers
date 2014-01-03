from scrapelib import Scraper

class InvalidHTTPSScraper(Scraper):
    def request(self, *args, **kwargs):
        return super(InvalidHTTPSScraper, self).request(
            *args, verify=False, **kwargs)
