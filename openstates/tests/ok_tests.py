"""Test the Oklahoma scraping classes."""

import unittest

import openstates
import openstates.tests
from openstates.ok.bills import OKBillScraper

class TestOK(unittest.TestCase):

    def setUp(self):
        openstates.tests.setup()

    def test_missing_action_bug_issue_201(self):
        # Test issue 201.
        metadata = {'session_details': {1200: {'session_id': 1200}}}
        scraper = OKBillScraper(metadata)
        bills = scraper.scrape('upper', 1200, only_bills=set(['SB1959']))
        self.assertEqual(1, len(bills))
        actions = openstates.tests.get_bill_data('SB1959')['actions']
        self.assertEqual(25, len(actions))

        bills = scraper.scrape('upper', 1200, only_bills=set(['SJR2231']))
        self.assertEqual(0, len(bills))

    def tearDown(self):
        openstates.tests.teardown()

if __name__ == '__main__':
    unittest.main()
