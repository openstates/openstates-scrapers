import datetime
import re

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import Bill, BillScraper

class NDBillScraper(BillScraper):
    """
    Scrapes available legislative information from the website of the North
    Dakota legislature and stores it in the fiftystates backend.
    """
    state = 'nd'
    site_root = 'http://www.legis.nd.gov'

    def scrape(self, chamber, session):
        # URL building
        if chamber == 'upper':
            url_chamber_name = 'senate'
            norm_chamber_name = 'Senate'
        else:
            url_chamber_name = 'house'
            norm_chamber_name = 'House'

        assembly_url = '/assembly/%s' % session

        chamber_url = '/bill-text/%s-bill.html' % (url_chamber_name)

        bills_list_url = self.site_root + assembly_url + chamber_url

        with self.urlopen(bill_list_url) as html:
            list_page = lxml.html.fromstring(html)


