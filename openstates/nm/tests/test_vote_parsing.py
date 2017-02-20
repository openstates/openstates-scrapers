#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import datetime
from nose.tools import ok_, eq_
from shutil import copy
from openstates.nm import NMBillScraper, metadata
from os import listdir, getcwd, path 

class TestVoteParsing(object):
    def setup(self):
        self.nmBillScraper=NMBillScraper(metadata, '/tmp', True)

    def testsenateparsing(self):
        """Parsing Senate vote"""
        
        '''This will run the parser over any *senate.pdf in the testData folder
           If vote is in the voteKey, it will also do an additional check, 
           otherwise the only test being done is the sanity check in the parser'''
        
        #print vote on a known good result to generate this easily
        voteKey={'2017_vote_senate.pdf':
                     {'other_count': 1, '_type': 'vote', 'chamber': 'upper', 'yes_count': 39, 'yes_votes': ['CANDELARIA', 'PINTO', 'LOPEZ', 'SOULES', 'BACA', 'ORTIZ y PINO', 'INGLE', 'SAPIEN', 'CERVANTES', 'PIRTLE', u'MUQOZ', 'WHITE', 'MARTINEZ', 'STEFANICS', 'PADILLA', 'NEVILLE', 'WIRTH', 'IVEY-SOTO', 'SHARER', 'CISNEROS', 'RODRIGUEZ', 'McSORLEY', 'STEINBORN', 'BURT', 'PAPEN', 'KERNAN', 'SHENDO', "O'NEILL", 'GOULD', 'RUE', 'STEWART', 'CAMPOS', 'PAYNE', 'LEAVELL', 'SMITH', 'GRIGGS', 'SANCHEZ', 'MORALES', 'TALLMAN'], 'other_votes': ['MOORES'], 'motion': 'senate passage', 'sources': [{'url': '2017_vote_senate.pdf'}], 'passed': True, 'date': datetime.datetime(2017, 1, 18, 0, 0), 'type': 'other', 'no_count': 2, 'no_votes': ['BRANDT', 'WOODS']}
                 }
        testData=path.join(getcwd(), 'tests/testData')
        cacheData=path.join(getcwd(), 'tests/cacheData')
        pdfs=[f for f in listdir(testData) if 'senate' in f and '.pdf' in f]
        for pdf in pdfs:
            copy(path.join(testData, pdf), path.join(cacheData, pdf))
            sv_text=self.nmBillScraper.scrape_vote(path.join(cacheData, pdf), True)
            vote=self.nmBillScraper.parse_senate_vote(sv_text, pdf)
            ok_(vote, 'Vote returned empty or did not complete')
            if pdf in voteKey:
                eq_(vote, voteKey[pdf], '%s Vote results did not match up with redefined key' % pdf) 

    def testhouseparsing(self):
        """Parsing House vote"""
        
        '''This will run the parser over any *house.pdf in the testData folder
           If vote is in the voteKey, it will also do an additional check, 
           otherwise the only test being done is the sanity check in the parser'''
        
        #print vote on a known good result to generate this easily
        voteKey={'2017_vote_senate.pdf':
                    {'other_count': 1, '_type': 'vote', 'chamber': 'upper', 'yes_count': 39, 'yes_votes': ['CANDELARIA', 'PINTO', 'LOPEZ', 'SOULES', 'BACA', 'ORTIZ y PINO', 'INGLE', 'SAPIEN', 'CERVANTES', 'PIRTLE', u'MU\xd1OZ', 'WHITE', 'MARTINEZ', 'STEFANICS', 'PADILLA', 'NEVILLE', 'WIRTH', 'IVEY-SOTO', 'SHARER', 'CISNEROS', 'RODRIGUEZ', 'McSORLEY', 'STEINBORN', 'BURT', 'PAPEN', 'KERNAN', 'SHENDO', "O'NEILL", 'GOULD', 'RUE', 'STEWART', 'CAMPOS', 'PAYNE', 'LEAVELL', 'SMITH', 'GRIGGS', 'SANCHEZ', 'MORALES', 'TALLMAN'], 'other_votes': ['MOORES'], 'motion': 'senate passage', 'sources': [{'url': '2017_vote_senate.pdf'}], 'passed': False, 'date': datetime.datetime(2017, 1, 18, 0, 0), 'type': 'other', 'no_count': 2, 'no_votes': ['BRANDT', 'WOODS'], 'passed': True
                     }
                 }
        testData=path.join(getcwd(), 'tests/testData')
        cacheData=path.join(getcwd(), 'tests/cacheData')
        pdfs=[f for f in listdir(testData) if 'house' in f and '.pdf' in f]
        for pdf in pdfs:
            copy(path.join(testData, pdf), path.join(cacheData, pdf))
            hv_text=self.nmBillScraper.scrape_vote(path.join(cacheData, pdf), True)
            vote=self.nmBillScraper.parse_house_vote(hv_text, pdf)
            ok_(vote, 'Vote returned empty or did not complete')
            if pdf in voteKey:
                eq_(vote, voteKey[pdf], '%s Vote results did not match up with redefined key' % pdf) 

if __name__ == '__main__':
    unittest.main()




