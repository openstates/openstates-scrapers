import datetime

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote


class EXBillScraper(BillScraper):
    state = 'ex'

    def scrape(self, chamber, year):
        if year != '2009':
            raise NoDataForPeriod(year)

        session = '2009-2010'

        if chamber == 'upper':
            other_chamber = 'lower'
            bill_id = 'SB 1'
        else:
            other_chamber = 'upper'
            bill_id = 'HB 1'

        b1 = Bill(session, chamber, bill_id, 'A super bill')
        b1.add_source('http://example.com/')
        b1.add_version('As Introduced', 'http://example.com/SB1.html')
        b1.add_document('Google', 'http://google.com')
        b1.add_sponsor('primary', 'Bob Smith')
        b1.add_sponsor('secondary', 'Johnson, Sally')

        d1 = datetime.datetime.strptime('1/29/2010', '%m/%d/%Y')
        v1 = Vote('upper', d1, 'Final passage', True, 2, 0, 0)
        v1.yes('Smith')
        v1.yes('Johnson')

        d2 = datetime.datetime.strptime('1/30/2010', '%m/%d/%Y')
        v2 = Vote('lower', d2, 'Final passage', False, 0, 1, 1)
        v2.no('Bob Smith')
        v2.other('S. Johnson')

        b1.add_vote(v1)
        b1.add_vote(v2)

        b1.add_action(chamber, 'introduced', d1)
        b1.add_action(chamber, 'read first time', d2)
        b1.add_action(other_chamber, 'introduced', d2)

        self.save_bill(b1)
