#!/usr/bin/env python
import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForPeriod)


def suite():
    suite = unittest.makeSuite(LegislationUtilsTestCase, "test")


class LegislationUtilsTest(unittest.TestCase):
    
    def testNoDataForPeriodException(self):
        yearError = NoDataForPeriod("1991");
        assert yearError.year == "1991", "Wrong Year"
        assert str(yearError) == "No data exists for 1991", (
            "Bad Error Message: " + str(yearError))
            
    def testDateEncoder(self):
        testDate = datetime.datetime(2009, 12, 01, 13, 14, 15, 0, )
        encoder = DateEncoder()
        timestamp = encoder.default(testDate)
        assert str(timestamp) == "1259691255.0", ("Bad Timestamp" +
                                                  str(timestamp))
