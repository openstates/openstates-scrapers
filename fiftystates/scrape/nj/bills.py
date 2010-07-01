import datetime

from fiftystates.scrape.nj import metadata
from fiftystates.scrape.nv.utils import chamber_name
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree

class NJBillScraper(BillScraper):
    state = 'nj'

    def scrape(self, chamber, year):

        if year < 1996:
            raise NoDataForYear(year)
        elif year == 1996:
            year_abr = 9697
        elif year == 1998:
            year_abr = 9899
        else:
            year_abr = year

        session = (int(year) - 2010) + 214
        self.scrape_bill_pages(year, session, year_abr)

    def scrape_bill_pages(self, year, session, year_abr):

        year_url = 'http://www.njleg.state.nj.us/bills/bills0001.asp'
        year_body = 'DBNAME=LIS%s' % (year_abr)
        bill_list_url = 'http://www.njleg.state.nj.us/bills/BillsByNumber.asp'
        first_body = 'SearchText=&SubmitSearch=Find&GoToPage=1&MoveRec=&DocumentText=&Search=&NewSearch=&ClearSearch=&SearchBy'
        with self.urlopen(year_url, 'POST', year_body) as year_page:
            with self.urlopen(bill_list_url, 'POST', first_body) as first_bill_page:
                root = lxml.etree.fromstring(first_bill_page, lxml.etree.HTMLParser())
                num_pages = root.xpath('string(//table/tr[1]/td[4]/div/font/b/font)').split()[-1]
                num_pages = int(num_pages)
                #self.scrape_bills_number(page)
                print num_pages


    def scrape_bill_number(self, page):
        "Holder for scraping the bill numbers off a page"


