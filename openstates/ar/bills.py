import csv
import StringIO

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

            self.save_bill(bill)
