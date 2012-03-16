# Copyright (c) 2012 Google, Inc. All rights reserved.

"""Test the New York scraping classes."""

import unittest

import openstates
import openstates.tests
from openstates.ny.committees import NYCommitteeScraper

class TestNY(unittest.TestCase):

    def setUp(self):
    	openstates.tests.setup()

    def test_bad_committees_issue_195(self):
    	# Test issue 195.
    	scraper = NYCommitteeScraper(None)
    	committees = []
    	committees += scraper.scrape('upper', None, set(['State-Native American Relations']))
    	committees += scraper.scrape('lower', None, set(['State-Native American Relations']))
    	self.assertEqual(0, len(committees))

    def tearDown(self):
    	openstates.tests.teardown()

if __name__ == '__main__':
    unittest.main()