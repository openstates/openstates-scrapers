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

        self.bills = {}
        self.scrape_bill_info(chamber, session)
        self.scrape_bill_history()

        for bill in self.bills.itervalues():
            self.save_bill(bill)

    def scrape_bill_info(self, chamber, session):
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
            self.bills[bill_id] = bill

    def scrape_bill_history(self):
        history_url = "ftp://ftp.cga.ct.gov/pub/data/bill_history.csv"
        page = urllib2.urlopen(history_url)
        page = csv.DictReader(page)

        for row in page:
            bill_id = row['bill_num']

            try:
                bill = self.bills[bill_id]
            except KeyError:
                continue

            action = row['act_desc']
            date = row['act_date']
            date = datetime.datetime.strptime(
                date, "%Y-%m-%d %H:%M:%S").date()

            bill.add_action(bill['chamber'], action, date)
