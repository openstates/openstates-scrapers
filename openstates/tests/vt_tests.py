"""Test the Vermont scraping classes."""

import unittest

import openstates
import openstates.tests
from openstates.vt.bills import VTBillScraper

class TestVT(unittest.TestCase):

    def setUp(self):
        openstates.tests.setup()

    def test_bad_votes_bug_issue_166(self):
        # Test issue 166.
        metadata = {'session_details': {'2012-2012': {'session_id': '2012-2012'}}}
        scraper = VTBillScraper(metadata)
        # Check that 'Not Voting' is recoreded properly
        bills = scraper.scrape('lower', '2012-2012', only_bills=set(['H.0258']))
        self.assertEqual(1, len(bills))
        bill = openstates.tests.get_bill_data('H.0258')
        votes = bill['votes']
        for vote in votes:
            self.assertEqual(vote['other_count'], len(vote['other_votes']))

        # Check for non-existent bills.
        bills = scraper.scrape('lower', '2012-2012', only_bills=set(['HR0015', 'HR0007']))
        self.assertEqual(0, len(bills))

        # Confirm sponsorless bill.
        bills = scraper.scrape('lower', '2012-2012', only_bills=set(['HR0003']))
        self.assertEqual(1, len(bills))
        bill = openstates.tests.get_bill_data('HR0003')
        self.assertEqual(0, len(bill['sponsors']))



    def tearDown(self):
        openstates.tests.teardown()

if __name__ == '__main__':
    unittest.main()
