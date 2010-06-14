from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill

import re
import datetime as dt
import lxml.html


class HIBillScraper(BillScraper):
    state = 'hi'

    def scrape(self, chamber, year):
        session = "%s-%d" % (year, int(year) + 1)

        if int(year) >= 2009:
            self.scrape_session_new(chamber, session)
        else:
            self.scrape_session_old(chamber, session)

    def scrape_session_new(self, chamber, session):
        pass

    def scrape_session_old(self, chamber, session):
        pass