# Copyright (c) 2012 Google, Inc. All rights reserved.

"""Test the Arizona scraping classes."""

import unittest

import openstates
import openstates.tests
from openstates.az.bills import AZBillScraper

class TestAZ(unittest.TestCase):

    def setUp(self):
    	openstates.tests.setup()

    def test_bad_votes_issue_197(self):
    	# Test issue #197.
    	# Test that we count misc votes
    	metadata = {'session_details': {'50th-2nd-regular': {'session_id': 107}}}
    	scraper = AZBillScraper(metadata)
    	bills = scraper.scrape('upper', '50th-2nd-regular', set(['MIS 001']))
    	self.assertEqual(1, len(bills))
    	votes = openstates.tests.get_bill_data('MIS 001')['votes']
    	self.assertEqual(1, len(votes))

    	# Test that we count AB = Absent
    	metadata = {'session_details': {'49th-1st-regular': {'session_id': 87}}}
    	scraper = AZBillScraper(metadata)
    	bills = scraper.scrape('lower', '49th-1st-regular', set(['HB 2610']))
    	self.assertEqual(1, len(bills))
    	votes = openstates.tests.get_bill_data('HB 2610')['votes']
    	self.assertEqual(5, len(votes))
    	for vote in votes:
    		self.assertEqual(vote['other_count'], len(vote['other_votes']))



    def tearDown(self):
    	openstates.tests.teardown()

if __name__ == '__main__':
    unittest.main()