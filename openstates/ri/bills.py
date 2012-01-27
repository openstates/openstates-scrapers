import datetime as dt
import lxml.html

from billy.scrape.bills import BillScraper, Bill

class RIBillScraper(BillScraper):
    state = 'ri'

    def scrape(self, chamber, session):
        print chamber, session
