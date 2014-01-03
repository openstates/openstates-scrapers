from scrapelib import Scraper

class InvalidHTTPSScraper(Scraper):
    def request(*args, **kwargs):
        return super(InvalidHTTPSScraper, self).request(
            *args, verify=False, **kwargs)
