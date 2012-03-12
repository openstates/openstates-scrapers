# Copyright (c) 2012 Google, Inc. All rights reserved.

"""Run all of the tests in the files in this directory.

Be sure to update this file as more test files are added."""

import unittest

import ok_tests
import openstates.tests

def main(testdata):
	openstates.tests.set_testdata_dir(testdata)
	loader = unittest.TestLoader()
	suites = []
	suites.append(loader.loadTestsFromTestCase(ok_tests.TestOK))
	alltests = unittest.TestSuite(suites)
	unittest.TextTestRunner(verbosity=2).run(alltests)