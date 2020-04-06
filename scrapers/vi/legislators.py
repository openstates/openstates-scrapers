from openstates.scrape import Person, Scraper
from utils import LXMLMixin


class VIPersonScraper(Scraper, LXMLMixin):
    def scrape(self, chamber, term):
        pass
        yield Person()
        # home_url = 'http://www.legvi.org/'
        # doc = lxml.html.fromstring(self.get(url=home_url).text)

        # USVI offers name, island, and biography, but contact info is locked up in a PDF
        # //*[@id="sp-main-menu"]/ul/li[2]/div/div/div/div/ul/li/div/div/ul/li/a/span/span
