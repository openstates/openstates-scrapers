import unittest
import random
import unittest

import openstates.ks.action_codes_scrape

class TestNames(unittest.TestCase):

    def testNames (self):
        print "test kansas"

    def parse_action_codes (self):
	openstates.ks.action_codes_scrape.parse_action_codes('openstates/ks/action_codes')
#        print openstates.ks.action_codes_scrape.voted_codes
#        print openstates.ks.action_codes_scrape.passed_codes 
#        print openstates.ks.action_codes_scrape.failed_codes 
#        print openstates.ks.action_codes_scrape.numbers
	print openstates.ks.action_codes_scrape.new_numbers

    def runTest(self ):
        print "Hello"
        self.testNames()
        self.parse_action_codes()


# action_codes_scrape.py

suite = TestNames
