# Copyright (c) 2012 Google, Inc. All rights reserved.

"""Run all of the tests in the files in this directory.

Be sure to update this file as more test files are added."""

import doctest
import unittest

import openstates.ny.committees
import openstates.tests

import az_tests
import me_tests
import ny_tests
import ok_tests
import va_tests
import vt_tests
import wy_tests

def main(testdata):
	openstates.tests.set_testdata_dir(testdata)
	loader = unittest.TestLoader()
	suites = []
	suites.append(loader.loadTestsFromTestCase(az_tests.TestAZ))
	suites.append(loader.loadTestsFromTestCase(me_tests.TestME))
	suites.append(loader.loadTestsFromTestCase(ny_tests.TestNY))
	suites.append(loader.loadTestsFromTestCase(ok_tests.TestOK))
	suites.append(loader.loadTestsFromTestCase(va_tests.TestVA))
	suites.append(loader.loadTestsFromTestCase(vt_tests.TestVT))
	suites.append(loader.loadTestsFromTestCase(wy_tests.TestWY))
	alltests = unittest.TestSuite(suites)
	unittest.TextTestRunner(verbosity=2).run(alltests)
	
	# Also test docstrings.
	doctest.testmod(openstates.ny.committees)