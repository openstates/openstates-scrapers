#!/usr/bin/env python
import sys
import os
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)


class ExampleLegislationScraper(LegislationScraper):

    state = 'ex'

    metadata = {
        'state_name': 'Example State',
        'legislature_name': 'Example Legislature',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Regresentative',
        'upper_term': 6,
        'lower_term': 2,
        'sessions': ['2007-2008', '2009-2010'],
        'session_details': {
            '2007-2008': {'years': [2007, 2008], 'sub_sessions':
                              ['Sub Session 1', 'Sub Session 2']},
            '2009-2010': {'years': [2009, 2010], 'sub_sessions': []}}}

    def scrape_bills(self, chamber, year):
        if year != '2009':
            raise NoDataForYear

        if chamber == 'upper':
            other_chamber = 'lower'
            bill_id = 'SB 1'
        else:
            other_chamber = 'upper'
            bill_id = 'HB 1'

        b1 = Bill('2009-2010', chamber, bill_id, 'A super bill')
        b1.add_source('http://example.com')
        b1.add_version('As Introduced', 'http://example.com/SB1.html')
        b1.add_document('Google', 'http://google.com')
        b1.add_sponsor('primary', 'Bob Smith')
        b1.add_sponsor('secondary', 'Johnson, Sally')

        d1 = datetime.datetime.strptime('1/29/2010', '%m/%d/%Y')
        v1 = Vote('upper', d1, 'Final passage',
                  True, 2, 0, 0)
        v1.yes('Bob Smith')
        v1.yes('Sally Johnson')

        d2 = datetime.datetime.strptime('1/30/2010', '%m/%d/%Y')
        v2 = Vote('lower', d2, 'Final passage',
                  False, 0, 1, 1)
        v2.no('B. Smith')
        v2.other('Sally Johnson')

        b1.add_vote(v1)
        b1.add_vote(v2)

        b1.add_action(chamber, 'introduced', d1)
        b1.add_action(chamber, 'read first time', d1)
        b1.add_action(other_chamber, 'introduced', d2)

        self.add_bill(b1)

    def scrape_legislators(self, chamber, year):
        if year != '2009':
            raise NoDataForYear

        l1 = Legislator('2009-2010', chamber, '1st',
                        'Bob Smith', 'Bob', 'Smith', '',
                        'Democrat')

        if chamber == 'upper':
            l1.add_role('President of the Senate', '2009-2010')
        else:
            l1.add_role('Speaker of the House', '2009-2010')

        l1.add_source('http://example.com/Bob_Smith.html')

        l2 = Legislator('2009-2010', chamber, '2nd',
                        'Sally Johnson', 'Sally', 'Johnson', '',
                        'Republican')
        l2.add_role('Minority Leader', '2009-2010')
        l2.add_source('http://example.com/Sally_Johnson.html')

        self.add_legislator(l1)
        self.add_legislator(l2)


if __name__ == '__main__':
    ExampleLegislationScraper.run()
