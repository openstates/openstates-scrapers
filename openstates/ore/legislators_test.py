#!/usr/bin/env python

import unittest
import legislators
from os import path

class LegislatorsTest(unittest.TestCase):

    def setUp(self):
        self.s = legislators.ORELegislatorScraper(None)
        self.leg = [ ]
        self.s.save_legislator = lambda l: self.leg.append(l)
        self.s.rawdata = open(path.join(path.dirname(__file__),'testdata/members.xml')).read()

    def testCanParseSenate(self):
        self.s.scrape('upper', '2011')
        self.assertEquals(30, len(self.leg))

    def testCanParseHouse(self):
        self.s.scrape('lower', '2011')
        self.assertEquals(60, len(self.leg))
        
    def testPhoneNumbers(self):
        self.s.scrape('upper', '2011')
        self.assertTrue(len(self.leg) > 0)
        l = self.leg[0]
        self.assertEquals('541-555-9207', l['district_phone'])
        self.assertEquals('503-986-1702', l['phone'])
        l = self.leg[2]
        self.assertEquals(False, l.has_key('district_phone'))
        self.assertEquals('503-986-1706', l['phone'])
        
if __name__ == '__main__':
    unittest.main()
