# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper

class MyScraper(LegislationScraper):
    #must set state attribute as the state's abbreviated name
    self.state = ''
    
    def scrape_legislators(self,chamber,year):
        pass

    def scrape_bills(self,chamber,year):
        pass
    
if __name__ == '__main__':
    MyScraper().run()
