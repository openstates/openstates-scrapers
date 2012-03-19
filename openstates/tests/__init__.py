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

def setup():
    global _old_scraper_save_object
    # Intercept requests to save objects to disk, so that we can inspect them.
    _old_scraper_save_object = Scraper.save_object
    Scraper.save_object = _fake_save_object

def teardown():
    Scraper.save_object = _old_scraper_save_object

# Internal stuff.

_scraper = scrapelib.Scraper(follow_robots=False)

def _fake_save_object(self, obj):
    if 'bill_id' in obj:
        saved_data[obj['bill_id']] = obj
    else:
        raise ValueError("Trying to save unknown data: %s" % obj)
