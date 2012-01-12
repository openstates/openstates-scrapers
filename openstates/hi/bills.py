import datetime as dt
import lxml.html

from urlparse import urlparse

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

HI_URL_BASE = "http://capitol.hawaii.gov/"

class HIBillScraper(BillScraper):
    
    state = 'hi'

    def scrape(self, chamber, session):
        pass
