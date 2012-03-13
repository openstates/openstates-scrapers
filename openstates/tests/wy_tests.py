# Copyright (c) 2012 Google, Inc. All rights reserved.

"""Test the Wyoming scraping classes."""

import unittest

import openstates
import openstates.tests
from openstates.wy.bills import WYBillScraper

class TestWY(unittest.TestCase):

    def setUp(self):
    	openstates.tests.setup()

    def test_bad_bill_issue_169(self):
    	# Test issue #169
    	# Test that we grab all roll calls
    	metadata = {'session_details': {'2011': {'session_id': 2011}}}
    	scraper = WYBillScraper(metadata)
        only_bills = set(['HB0122', 'HB0036', 'HB0178', 'HB0001', 'HB0265'])
    	bills = scraper.scrape('lower', '2011', only_bills)
    	self.assertEqual(len(only_bills), len(bills))
    	bill = openstates.tests.get_bill_data('HB0122')
        # Check that the vote counts are correct.
    	self.assertEqual(3, len(bill['votes']))
        votes = bill['votes']
        self.assertEqual([6, 57, 1], [v['yes_count'] for v in votes])
        for vote in votes:
            self.assertEqual(vote['yes_count'], len(vote['yes_votes']))
            self.assertEqual(vote['no_count'], len(vote['no_votes']))
            self.assertEqual(vote['other_count'], len(vote['other_votes']))
        bill = openstates.tests.get_bill_data('HB0036')
        votes = bill['votes']
        for vote in votes:
            self.assertEqual(vote['yes_count'], len(vote['yes_votes']))
            self.assertEqual(vote['no_count'], len(vote['no_votes']))
            self.assertEqual(vote['other_count'], len(vote['other_votes']))
        bill = openstates.tests.get_bill_data('HB0178')
        votes = bill['votes']
        for vote in votes:
            self.assertEqual(vote['yes_count'], len(vote['yes_votes']))
            self.assertEqual(vote['no_count'], len(vote['no_votes']))
            self.assertEqual(vote['other_count'], len(vote['other_votes']))
        bill = openstates.tests.get_bill_data('HB0001')
        votes = bill['votes']
        for vote in votes:
            self.assertEqual(vote['yes_count'], len(vote['yes_votes']))
            self.assertEqual(vote['no_count'], len(vote['no_votes']))
            self.assertEqual(vote['other_count'], len(vote['other_votes']))
        # Check for a sponsor and actions.
        bill = openstates.tests.get_bill_data('HB0265')
        self.assertEqual(6, len(bill['sponsors']))
        self.assertEqual(4, len(bill['actions']))

    def tearDown(self):
    	openstates.tests.teardown()

if __name__ == '__main__':
    unittest.main()