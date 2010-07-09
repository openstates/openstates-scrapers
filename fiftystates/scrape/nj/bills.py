import datetime

from fiftystates.scrape.nj import metadata
from fiftystates.scrape.nv.utils import chamber_name
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree
from dbfpy import dbf
import scrapelib

class NJBillScraper(BillScraper):
    state = 'nj'

    def scrape(self, chamber, year):

        if year < 1996:
            raise NoDataForPeriod(year)
        elif year == 1996:
            year_abr = 9697
        elif year == 1998:
            year_abr = 9899
        else:
            year_abr = year

        session = (int(year) - 2010) + 214
        self.scrape_bill_pages(year, session, year_abr)

    def scrape_bill_pages(self, year, session, year_abr):

