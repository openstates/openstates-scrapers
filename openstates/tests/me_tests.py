# Copyright (c) 2012 Google, Inc. All rights reserved.

"""Test the Maine scraping classes."""

import unittest

import openstates
import openstates.tests
from openstates.me.bills import MEBillScraper

class TestME(unittest.TestCase):

    def setUp(self):
    	openstates.tests.setup()

    def test_no_sponsors_issue_173(self):
    	# Test issue #173
    	# Test that we grab sponsors
    	metadata = {'session_details': {'125': {'session_id': 9}}}
    	scraper = MEBillScraper(metadata)
        only_bills = set(['HP1174', 'HP1309', 'HP0415', 'HP0451', 'HP0329'])
    	bills = scraper.scrape('lower', '125', only_bills)
    	self.assertEqual(len(only_bills), len(bills))
        self.assertEqual(1, len(openstates.tests.get_bill_data('HP1174')['sponsors']))
        self.assertEqual(1, len(openstates.tests.get_bill_data('HP1309')['sponsors']))
        self.assertEqual(1, len(openstates.tests.get_bill_data('HP0415')['sponsors']))
        self.assertEqual(1, len(openstates.tests.get_bill_data('HP0451')['sponsors']))
        self.assertEqual(1, len(openstates.tests.get_bill_data('HP0329')['sponsors']))
        
    def tearDown(self):
    	openstates.tests.teardown()

if __name__ == '__main__':
    unittest.main()