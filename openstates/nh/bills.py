import zipfile
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import Bill, BillScraper

body_code = {'lower': 'H', 'upper': 'S'}
VERSION_URL = 'http://www.gencourt.state.nh.us/legislation/%s/%s.html'


class NHBillScraper(BillScraper):
    state = 'nh'

    def scrape(self, chamber, session):
        zip_url = 'http://gencourt.state.nh.us/downloads/Bill%20Status%20Tables.zip'

        fname, resp = self.urlretrieve(zip_url)
        zf = zipfile.ZipFile(open(fname))

        # bill basics
        self.bills = {}
        for line in zf.open('tbllsrs.txt').readlines():
            line = line.split('|')
            session_yr = line[0]
            lsr = line[1]
            title = line[2]
            body = line[3]
            billtype = line[4]
            expanded_bill_id = line[9]
            bill_id = line[10]

            if body == body_code[chamber] and session_yr == session:
                # TODO: billtype
                self.bills[lsr] = Bill(session, chamber, bill_id, title)
                version_url = VERSION_URL % (session,
                                             expanded_bill_id.replace(' ', ''))
                self.bills[lsr].add_version('latest version', version_url)

        # load legislators
        self.legislators = {}
        for line in zf.open('tbllegislators.txt').readlines():
            line = line.split('|')
            employee_num = line[0]

            # first, last, middle
            if line[3]:
                name = '%s %s %s' % (line[2], line[3], line[1])
            else:
                name = '%s %s' % (line[2], line[1])

            self.legislators[employee_num] = {'name': name,
                                              'seat': line[5]}
            #body = line[4]

        # sponsors
        for line in zf.open('tbllsrsponsors.txt').readlines():
            session_yr, lsr, seq, employee, primary = line.split('|')

            if session_yr == session and lsr in self.bills:
                sp_type = 'primary' if primary == '1' else 'cosponsor'
                self.bills[lsr].add_sponsor(sp_type,
                                    self.legislators[employee]['name'],
                                    _code=self.legislators[employee]['seat'])


        # actions
        for line in zf.open('tbldocket.txt').readlines():
            # a few blank/irregular lines, irritating
            if '|' not in line:
                continue

            (session_yr, lsr, _, timestamp, bill_id, body,
             action) = line.split('|')

            if session_yr == session and lsr in self.bills:
                actor = 'lower' if body == 'H' else 'upper'
                time = datetime.datetime.strptime(timestamp,
                                                  '%m/%d/%Y %H:%M:%S %p')
                self.bills[lsr].add_action(actor, action, time)


        # save all bills
        for bill in self.bills.values():
            bill.add_source(zip_url)
            self.save_bill(bill)
