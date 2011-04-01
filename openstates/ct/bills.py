import csv
import urllib2
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill


class CTBillScraper(BillScraper):
    state = 'ct'

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)

        info_url = "ftp://ftp.cga.ct.gov/pub/data/bill_info.csv"
        page = urllib2.urlopen(info_url)
        page = csv.DictReader(page)

        abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

        for row in page:
            bill_id = row['bill_num']
            if not bill_id[0] == abbrev:
                continue

            bill = Bill(session, chamber, bill_id, row['bill_title'])
            bill.add_source(info_url)
            self.save_bill(bill)
