from __future__ import with_statement
import os
import time
import logging
import urllib2
import datetime
import contextlib
from optparse import make_option, OptionParser

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates import settings

import scrapelib

try:
    from BeautifulSoup import BeautifulSoup
    USE_SOUP = True
except ImportError:
    print "BeautifulSoup not found, Scraper.soup_context will " \
        "be unavailable"
    USE_SOUP = False


class ScrapeError(Exception):
    """
    Base class for scrape errors.
    """
    pass


class NoDataForYear(ScrapeError):
    """
    Exception to be raised when no data exists for a given year
    """
    def __init__(self, year):
        self.year = year

    def __str__(self):
        return 'No data exists for %s' % self.year


class JSONDateEncoder(json.JSONEncoder):
    """
    JSONEncoder that encodes datetime objects as Unix timestamps.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return time.mktime(obj.timetuple())
        return json.JSONEncoder.default(self, obj)


class Scraper(scrapelib.Scraper):
    # The earliest year for which legislative data is available in
    # any state (used for --all)
    earliest_year = 1969

    def __init__(self, no_cache=False, output_dir=None, **kwargs):
        """
        Create a new Scraper instance.

        :param no_cache: if True, will ignore any cached downloads
        :param output_dir: the Fifty State data directory to use
        """
        if no_cache:
            kwargs['cache_dir'] = None
        elif 'cache_dir' not in kwargs:
            kwargs['cache_dir'] = getattr(settings, 'FIFTYSTATES_CACHE_DIR',
                                          None)

        if 'error_dir' not in kwargs:
            kwargs['error_dir'] = getattr(settings, 'FIFTYSTATES_ERROR_DIR',
                                          None)

        if 'requests_per_minute' not in kwargs:
            kwargs['requests_per_minute'] = None

        super(Scraper, self).__init__(**kwargs)

        if not hasattr(self, 'state'):
            raise Exception('Scrapers must have a state attribute')

        self.output_dir = output_dir

        # logging convenience methods
        self.logger = logging.getLogger("fiftystates")
        self.log = self.logger.info
        self.debug = self.logger.debug
        self.warning = self.logger.warning

    def urlopen(self, *args, **kwargs):
        # Grab data out of (headers, data) tuple
        return super(Scraper, self).urlopen(*args, **kwargs)[1]

    @contextlib.contextmanager
    def soup_context(self, url):
        """
        Like :method:`urlopen_context`, except returns a BeautifulSoup
        parsed document.
        """
        if not USE_SOUP:
            raise ScrapeError("BeautifulSoup does not seem to be installed.")

        body = self.urlopen(url)
        soup = BeautifulSoup(body)

        try:
            yield soup
        except:
            self.show_error(url, body)
            raise

class FiftystatesObject(dict):
    def __init__(self, type, **kwargs):
        super(FiftystatesObject, self).__init__()
        self['_type'] = type
        self['sources'] = []
        self.update(kwargs)

    def add_source(self, url, retrieved=None, **kwargs):
        """
        Add a source URL from which data related to this object was scraped.

        :param url: the location of the source
        """
        retrieved = retrieved or datetime.datetime.now()
        self['sources'].append(dict(url=url, retrieved=retrieved, **kwargs))
