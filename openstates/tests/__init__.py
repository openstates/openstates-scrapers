# Copyright (c) 2012 Google, Inc. All rights reserved.

"""Provides some helper methods for running tests on scrapers."""


import pickle
import os.path

import scrapelib
from billy.scrape.bills import BillScraper


# Public methods and data.
saved_data = {}

def get_bill_data(bill_id):
	"""Get the object saved for the given bill id."""
	return saved_data[bill_id]

def set_testdata_dir(testdata_dir):
	"""Load testdata from the named directory (and save to it upon test completion)."""
	global testdatafile
	global _testdata
	testdatafile = os.path.join(testdata_dir, 'html_data')
	if os.path.exists(testdatafile):
		with open(testdatafile) as data:
			_testdata = pickle.load(data)
	else:
		_testdata = {}

def setup():
	# Intercept HTTP traffic and serve from cache, or create cache based on fetched results.
	BillScraper.urlopen = _fake_url_open
	# Intercept requests to save objects to disk, so that we can inspect them.
	BillScraper.save_object = _fake_save_object

def teardown():
	if _update_testdata:
	  _write_testdata()

# Internal stuff.

_scraper = scrapelib.Scraper(follow_robots=False)
_testdata = None
_testdatafile = None
_update_testdata = False

def _write_testdata():
	"""Save the HTML cached data to a pickled file."""
	with open(_testdatafile, 'w') as outf:
		pickle.dump(_testdata, outf)

def _fake_url_open(self, url, method='GET', params=""):
	global _update_testdata
	# If we have no test data, we just return an empty string.
	if _testdata is None:
		return ""
	if (url, method, params) not in _testdata:
		txt = _scraper.urlopen(url, method, params)
		print "\nFetching", url, params
		_testdata[(url, method, params)] = str(txt)
		_update_testdata = True
		return txt
	else:
		return _testdata[(url, method, params)]

def _fake_save_object(self, obj):
	saved_data[obj['bill_id']] = obj