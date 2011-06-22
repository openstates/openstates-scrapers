from billy.scrape.bills import BillScraper, Bill

import lxml.html

class NMBillScraper(BillScraper):
    state = 'nm'

    def scrape(self, chamber, session):
        pass
