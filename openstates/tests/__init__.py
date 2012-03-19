"""Provides some helper methods for running tests on scrapers."""

import os.path
import pickle

import scrapelib
from billy.scrape import Scraper


# Public methods and data.
saved_data = {}

def get_bill_data(bill_id):
	"""Get the object saved for the given bill id."""
	return saved_data[bill_id]

def set_testdata_dir(testdata_dir):
	"""Load testdata from the named directory (and save to it upon test completion)."""
	global _testdatafile
	global _testdata
	_testdatafile = os.path.join(testdata_dir, 'html_data')
	if os.path.exists(_testdatafile):
		with open(_testdatafile) as data:
			_testdata = pickle.load(data)
	else:
		_testdata = {}

def setup():
	global _old_scraper_url_open
	global _old_scraper_save_object
	# Intercept HTTP traffic and serve from cache, or create cache based on fetched results.
	_old_scraper_url_open = Scraper.urlopen
	Scraper.urlopen = _fake_url_open
	# Intercept requests to save objects to disk, so that we can inspect them.
	_old_scraper_save_object = Scraper.save_object
	Scraper.save_object = _fake_save_object

def teardown():
	if _update_testdata:
        _write_testdata()
	Scraper.urlopen = _old_scraper_url_open
	Scraper.save_object = _old_scraper_save_object

# Internal stuff.

_scraper = scrapelib.Scraper(follow_robots=False)
_testdata = None
_testdatafile = None
_update_testdata = False

def _write_testdata():
	"""Save the HTML cached data to a pickled file."""
	if _testdatafile is None:
		return
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
	return _testdata[(url, method, params)]


def _fake_save_object(self, obj):
	if 'bill_id' in obj:
		saved_data[obj['bill_id']] = obj
	else:
		print "Trying to save unknown data: %s" % obj
