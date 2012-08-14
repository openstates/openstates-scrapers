#!/usr/bin/env python


'''
 Author: Berlin Brown
 source : http://berlinbrowndev.blogspot.de/2008/05/running-google-appengine-django-unit.html

 hacked by JamesMichaelDuPont
 Filename: run_all_tests.py 
 ghostnet->the-anti-corruption-pledge ->sunlight foundation openstates
 Application: test case for sunlight foundation openstates
 Environment: Python 2.5.2
 -------------------------- Description --

 With the following code, you can run google-appengine
 stand-alone database driven test cases.

 * Run batch python unit test scripts
 * The script ensures that the google libraries are imported and
   added to the python sys path.
 
'''

import os
import sys
import unittest

DIR_PATH = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
PROJECT_HOME = os.path.join(DIR_PATH, '..', '..')

print("INFO: project_home=%s" % PROJECT_HOME)

EXTRA_PATHS = [
  DIR_PATH,
  os.path.join(PROJECT_HOME, 'openstates'),
  os.path.join(PROJECT_HOME, 'openstates', 'ks'),
]

sys.path = EXTRA_PATHS + sys.path
print EXTRA_PATHS

import datetime
import logging

APP_ID = 'sunlightfoundations_tests'
HIST_PATH = '/tmp/dev_ds_tests.hist'

# --------------
# Tests includes
# --------------
from tests.kansas_tests import suite as suite_kansas

def run_test_suite():
        suite = unittest.TestSuite()
        suite.addTest(suite_kansas())
        runner = unittest.TextTestRunner()
        runner.run(suite)

if __name__ == '__main__':
        print "Running model create"    
        run_test_suite()
        print "Done"
