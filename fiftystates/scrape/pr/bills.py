from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill

import lxml.html

class PRBillScraper(BillScraper):
    state = 'pr'
                    
    def scrape(self, chamber, year):    
        pass

                        
                           
                        
                    
                