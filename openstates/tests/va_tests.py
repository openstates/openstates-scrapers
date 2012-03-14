# Copyright (c) 2012 Google, Inc. All rights reserved.

"""Test the Virginia scraping classes."""

import unittest

import openstates
import openstates.tests
from openstates.va.bills import VABillScraper

class TestVA(unittest.TestCase):

    def setUp(self):
    	openstates.tests.setup()

    def test_no_sponsors_issue_167(self):
    	# Test issue #167
    	# Test that we get the right vote counts.
    	metadata = {'session_details': {'2011': {'site_id': 111}, '2012': {'site_id': 121}}}
    	scraper = VABillScraper(metadata)
        only_bills = set(['HB 1585', 'HB 2099', 'HB 2316'])
    	bills = scraper.scrape('lower', '2011', only_bills)
    	self.assertEqual(len(only_bills), len(bills))
        for bill_id in only_bills:
            votes = openstates.tests.get_bill_data(bill_id)['votes']
            for vote in votes:
                # Some votes have no information available.
                if len(vote['yes_votes']) == 0 and len(vote['no_votes']) == 0 and len(vote['other_votes']) == 0:
                    continue
                self.assertEqual(vote['yes_count'], len(vote['yes_votes']))
                self.assertEqual(vote['no_count'], len(vote['no_votes']))
                self.assertEqual(vote['other_count'], len(vote['other_votes']))

        only_bills = set(['HB 908', 'HB 459'])
        bills = scraper.scrape('lower', '2012', only_bills)
        self.assertEqual(len(only_bills), len(bills))
        for bill_id in only_bills:
            votes = openstates.tests.get_bill_data(bill_id)['votes']
            for vote in votes:
                # Some votes have no information available.
                if len(vote['yes_votes']) == 0 and len(vote['no_votes']) == 0 and len(vote['other_votes']) == 0:
                    continue
                self.assertEqual(vote['yes_count'], len(vote['yes_votes']))
                self.assertEqual(vote['no_count'], len(vote['no_votes']))
                self.assertEqual(vote['other_count'], len(vote['other_votes']))

        only_bills = set(['SB 432'])
        bills = scraper.scrape('upper', '2012', only_bills)
        self.assertEqual(len(only_bills), len(bills))
        for bill_id in only_bills:
            votes = openstates.tests.get_bill_data(bill_id)['votes']
            for vote in votes:
                # Some votes have no information available.
                if len(vote['yes_votes']) == 0 and len(vote['no_votes']) == 0 and len(vote['other_votes']) == 0:
                    continue
                self.assertEqual(vote['yes_count'], len(vote['yes_votes']))
                self.assertEqual(vote['no_count'], len(vote['no_votes']))
                self.assertEqual(vote['other_count'], len(vote['other_votes']))
        
    def tearDown(self):
    	openstates.tests.teardown()

if __name__ == '__main__':
    unittest.main()