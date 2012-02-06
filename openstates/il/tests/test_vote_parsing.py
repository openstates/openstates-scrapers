#!/usr/bin/env python

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
class TestVoteParsing(object):
    def test_find_and_parse(self):
        d = find_columns_and_parse(TEST_LINES1)
        eq_('E', d['Acevedo'])
        eq_('Y', d['Davis,William'])
        eq_('Y', d['Dunkin'])
        eq_('N', d['Durkin'])
        eq_('Y', d['Lyons'])
        eq_('N', d['Reis'])

        d = find_columns_and_parse(TEST_LINES2)
        eq_('NV', d['Cronin'])
        eq_('Y', d['Holmes'])
        eq_('N', d['Murphy'])
        eq_('Y', d['Mr. President'])
        eq_('P', d['Peterson'])

    def test_find_columns(self):
        columns = find_columns(TEST_LINES1)
        eq_(4,len(columns))
        a,b,c,d = columns
        eq_(0,a)
        eq_(19,b)
        eq_(39,c)
        eq_(60,d)

        columns = find_columns(TEST_LINES2)
        eq_(4,len(columns))
        a,b,c,d = columns
        eq_(0,a)
        eq_(17,b)
        eq_(34,c)
        eq_(52,d)

if __name__ == '__main__':
    unittest.main()

