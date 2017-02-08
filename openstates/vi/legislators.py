import re
import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class VILegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'vi'
    
    def scrape(self, chamber, term):
        home_url = 'http://www.legvi.org/'
        doc = lxml.html.fromstring(self.get(url=home_url).text)
        
        #USVI offers name, island, and biography, but contact info is locked up in a PDF
        #//*[@id="sp-main-menu"]/ul/li[2]/div/div/div/div/ul/li/div/div/ul/li/a/span/span
        links = doc.xpath('//*[@id="sp-main-menu"]/ul/li[2]/div/div/div/div/ul/li/div/div/ul/li/a/span/span')
        
        
        