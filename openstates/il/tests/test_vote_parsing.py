#!/usr/bin/env python
# -*- coding: utf-8 -*-
from nose.tools import *
import unittest
from openstates.il import metadata
from openstates.il.bills import find_columns, find_columns_and_parse
import logging

log = logging.getLogger('openstates.il.tests.test_bill_metadata')

TEST_LINES1 = [
    'E   Acevedo        Y   Davis,Monique   Y   Jefferson        Y   Reboletti',
    'Y   Arroyo         Y   Davis,William   Y   Joyce            N   Reis',
    'Y   Bassi          Y   DeLuca          N   Kosel            Y   Reitz',
    'N   Beaubien       Y   Dugan           Y   Lang             Y   Riley',
    'Y   Beiser         Y   Dunkin          N   Leitch           Y   Rita',
    'E   Bellock        N   Durkin          Y   Lyons            Y   Rose',
 ]
TEST_LINES2 =  [
    'Y    Althoff     Y    Dillard     N   Lauzen        NV   Righter',
    'NV   Bivins      Y    Forby       Y   Lightford     P    Risinger',
    'Y    Bomke       Y    Frerichs    Y   Link          Y    Rutherford',
    'Y    Bond        Y    Garrett     Y   Luechtefeld   Y    Sandoval',
    'N    Brady       NV   Haine       Y   Maloney       Y    Schoenberg',
    'N    Burzynski   Y    Halvorson   Y   Martinez      Y    Silverstein',
    'Y    Clayborne   Y    Harmon      Y   Meeks         Y    Steans',
    'Y    Collins     Y    Hendon      Y   Millner       Y    Sullivan',
    'NV   Cronin      Y    Holmes      Y   Munoz         P    Syverson',
    'Y    Crotty      Y    Hultgren    N   Murphy        Y    Trotter',
    'Y    Cullerton   Y    Hunter      Y   Noland        Y    Viverito',
    'Y    Dahl        Y    Jacobs      Y   Pankau        Y    Watson',
    'Y    DeLeo       Y    Jones, J.   P   Peterson      Y    Wilhelmi',
    'Y    Delgado     Y    Koehler     Y   Radogno       Y    Mr. President',
    'Y    Demuzio     Y    Kotowski    Y   Raoul',
]

TEST_LINES3 = [
    'Y    Althoff       Y    Haine         Y    Lightford     Y   Raoul',
    'Y    Bivins        Y    Harmon        NV   Link          Y   Rezin',
    'Y    Bomke         Y    Holmes        Y    Luechtefeld   Y   Righter',
    'Y    Brady         Y    Hunter        Y    Maloney       Y   Sandack',
    'Y    Clayborne     Y    Hutchinson    Y    Martinez      Y   Sandoval',
    'Y    Collins, A.   N    Jacobs        Y    McCann        Y   Schmidt',
    'Y    Collins, J.   Y    Johnson, C.   Y    McCarter      Y   Schoenberg',
    'Y    Crotty        Y    Johnson, T.   Y    Meeks         Y   Silverstein',
    'Y    Cultra        Y    Jones, E.     Y    Millner       Y   Steans',
    'Y    Delgado       Y    Jones, J.     Y    Mulroe        Y   Sullivan',
    'Y    Dillard       Y    Koehler       Y    Mu\xc3\xb1oz         Y   Syverson',
    'Y    Duffy         NV   Kotowski      Y    Murphy        Y   Trotter',
    'Y    Forby         Y    LaHood        Y    Noland        Y   Wilhelmi',
    'Y    Frerichs      Y    Landek        Y    Pankau        Y   Mr. President',
    'NV   Garrett       Y    Lauzen        Y    Radogno',
]

TEST_LINES1 = map(lambda x: x.decode('utf-8'), TEST_LINES1)
TEST_LINES2 = map(lambda x: x.decode('utf-8'), TEST_LINES2)
TEST_LINES3 = map(lambda x: x.decode('utf-8'), TEST_LINES3)

class TestVoteParsing(object):
    def test_find_and_parse1(self):
        d = find_columns_and_parse(TEST_LINES1)
        eq_('E', d['Acevedo'])
        eq_('Y', d['Davis,William'])
        eq_('Y', d['Dunkin'])
        eq_('N', d['Durkin'])
        eq_('Y', d['Lyons'])
        eq_('N', d['Reis'])

    def test_find_and_parse1(self):
        d = find_columns_and_parse(TEST_LINES2)
        eq_('NV', d['Cronin'])
        eq_('Y', d['Holmes'])
        eq_('N', d['Murphy'])
        eq_('Y', d['Mr. President'])
        eq_('P', d['Peterson'])

    def test_find_and_parse1(self):
        d = find_columns_and_parse(TEST_LINES3)
        eq_('Y', d['Collins, A.'])
        eq_('NV', d['Garrett'])
        eq_('Y', d[u'Muñoz'])
        eq_('Y', d['Syverson'])
        eq_('NV', d['Link'])



    def test_find_columns1(self):
        columns = find_columns(TEST_LINES1)
        eq_(4,len(columns))
        a,b,c,d = columns
        eq_(0,a)
        eq_(19,b)
        eq_(39,c)
        eq_(60,d)

    def test_find_columns2(self):
        columns = find_columns(TEST_LINES2)
        eq_(4,len(columns))
        a,b,c,d = columns
        eq_(0,a)
        eq_(17,b)
        eq_(34,c)
        eq_(52,d)

    def test_find_columns3(self):
        columns = find_columns(TEST_LINES3)
        eq_(4,len(columns))
        a,b,c,d = columns
        eq_(0,a)
        eq_(19,b)
        eq_(38,c)
        eq_(57,d)



if __name__ == '__main__':
    unittest.main()

