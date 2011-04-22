import csv
import StringIO
import datetime
import collections

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


class ARBillScraper(BillScraper):
    state = 'ar'

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)

        self.bills = {}
        self.scrape_bill_info(chamber, session)
        self.scrape_actions()

        for bill in self.bills.itervalues():
            self.save_bill(bill)

    def scrape_bill_info(self, chamber, session):
        url = "ftp://www.arkleg.state.ar.us/dfadooas/LegislativeMeasures.txt"
        page = self.urlopen(url).decode('latin-1')
        page = unicode_csv_reader(StringIO.StringIO(page), delimiter='|')

        for row in page:
            bill_chamber = {'H': 'lower', 'S': 'upper'}[row[0]]
            if bill_chamber != chamber:
                continue

            bill_id = "%s%s %s" % (row[0], row[1], row[2])

            bill = Bill('2011', chamber, bill_id, row[3])
            bill.add_source(url)
            bill.add_sponsor('lead sponsor', row[11])

            version_url = ("ftp://www.arkleg.state.ar.us/Bills/"
                           "%s/Public/%s.pdf" % (
                               session, bill_id.replace(' ', '')))
            bill.add_version(bill_id, version_url)

            self.bills[bill_id] = bill

    def scrape_actions(self):
        url = "ftp://www.arkleg.state.ar.us/dfadooas/ChamberActions.txt"
        page = self.urlopen(url)
        page = csv.reader(StringIO.StringIO(page))

        for row in page:
            bill_id = "%s%s %s" % (row[1], row[2], row[3])
            if bill_id not in self.bills:
                continue

            # Commas aren't escaped, but only one field (the action) can
            # contain them so we can work around it by using both positive
            # and negative offsets
            bill_id = "%s%s %s" % (row[1], row[2], row[3])
            actor = {'HU': 'lower', 'SU': 'upper'}[row[-5].upper()]
            date = datetime.datetime.strptime(row[6], "%Y-%m-%d %H:%M:%S")
            action = ','.join(row[7:-5])

            self.bills[bill_id].add_action(actor, action, date)
