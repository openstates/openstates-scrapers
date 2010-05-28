from __future__ import with_statement
from optparse import make_option, OptionParser
import datetime
import time
import os
import sys
import urllib2
import urlparse
import random
import contextlib
import logging
import warnings
import scrapelib

try:
    import json
except ImportError:
    import simplejson as json

try:
    from BeautifulSoup import BeautifulSoup
    USE_SOUP = True
except ImportError:
    print "BeautifulSoup not found, LegislationScraper.soup_context will " \
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
    option_list = (
        make_option('-y', '--year', action='append', dest='years',
                    help='year(s) to scrape'),
        make_option('--all', action='store_true', dest='all_years',
                    default=False, help='scrape all data (overrides --year)'),
        make_option('--upper', action='store_true', dest='upper',
                    default=False, help='scrape upper chamber'),
        make_option('--lower', action='store_true', dest='lower',
                    default=False, help='scrape lower chamber'),
        make_option('--nolegislators', action='store_false',
                    dest='legislators',
                    default=True, help="don't scrape legislator data"),
        make_option('-v', '--verbose', action='count', dest='verbose',
                    default=False,
                    help="be verbose (use multiple times for more"\
                        "debugging information)"),
        make_option('-d', '--output_dir', action='store', dest='output_dir',
                    help='output directory'),
        make_option('-n', '--no_cache', action='store_true', dest='no_cache',
                    help="don't use web page cache"),
        make_option('-r', '--rpm', action='store', type="int",
                    dest='requests_per_minute',
                    help="insert random delays wheen downloading web pages"),
    )

    metadata = {}

    # The earliest year for which legislative data is available in
    # any state (used for --all)
    earliest_year = 1969

    def __init__(self, verbosity=logging.INFO, no_cache=False,
                 output_dir=None, upper=True, lower=True,
                 legislators=True, all_years=True, years=[], **kwargs):
        """
        Create a new Scraper instance.

        :param verbosity: minimum level of messages to log (from the
          Python standard library's :mod:`logging` module)
        :param sleep: if True, will insert random sleeps between attempts
          to download pages
        :param no_cache: if True, will ignore any cached downloads
        :param output_dir: the Fifty State data directory to use
        """
        if no_cache:
            kwargs['cache_dir'] = None
        elif 'cache_dir' not in kwargs:
            kwargs['cache_dir'] = os.path.join('cache', self.state)

        if 'error_dir' not in kwargs:
            kwargs['error_dir'] = os.path.join('errors', self.state)

        if 'requests_per_minute' not in kwargs:
            kwargs['requests_per_minute'] = None

        super(Scraper, self).__init__(**kwargs)

        if not hasattr(self, 'state'):
            raise Exception('Scrapers must have a state attribute')

        self.output_dir = output_dir or os.path.join('data', self.state)
        self._init_dirs()

        self.logger = logging.getLogger("fiftystates")
        formatter = logging.Formatter("%(asctime)s %(levelname)s " +
                                      self.state + " %(message)s")
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        self.logger.addHandler(console)
        self.logger.setLevel(verbosity)

        # Convenience methods
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

    def _init_dirs(self):

        def makedir(path):
            try:
                os.makedirs(path)
            except OSError, e:
                if e.errno != 17 or os.path.isfile(self.output_dir):
                    raise e

        makedir(os.path.join(self.output_dir, "bills"))
        makedir(os.path.join(self.output_dir, "legislators"))
        makedir(os.path.join(self.output_dir, "committees"))

    def scrape_metadata(self):
        """
        Grab metadata about this state's legislature. Should return a
        dictionary with at least the following attributes:

        * `state_name`: the full name of this state, e.g. New Hampshire
        * `legislature name`: the name of this state's legislative body, e.g.
          `"Texas Legislature"`
        * `upper_chamber_name`: the name of the upper chamber of this state's
           legislature, e.g. `"Senate"`
        * `lower_chamber_name`: the name of the lower chamber of this
           state's legislature, e.g. `"House of Representatives"`
        * `upper_title`: the title of a member of this state's upper chamber,
           e.g. `"Senator"`
        * `lower_title`: the title of a member of this state's lower chamber,
           e.g. `"Representative"`
        * `upper_term`: the length, in years, of a term in this state's
           upper chamber, e.g. `4`
        * `lower_term`: the length, in years, of a term in this state's
           lower chamber, e.g. `2`
        * `sessions`: an ordered list of available sessions, e.g.
           `['2005-2006', '2007-2008', '2009-2010']
        * `session_details`: a dictionary, with an entry for each session
          indicating the years it encompasses as well as any 'sub' sessions,
          e.g.::

           {'2009-2010': {'years': [2009, 2010],
                          'sub_sessions': ["2009 Special Session 1"]}}

        """
        return self.metadata

    def write_metadata(self):
        metadata = self.scrape_metadata()
        metadata['state'] = self.state

        with open(os.path.join(self.output_dir, 'state_metadata.json'),
                  'w') as f:
            json.dump(metadata, f, cls=DateEncoder)

    @classmethod
    def run(cls):
        """
        Create and run a scraper for this state, based on
        command line options.
        """
        parser = OptionParser(
            option_list=cls.option_list)
        options, spares = parser.parse_args()

        if options.verbose == 0:
            verbosity = logging.WARNING
        elif options.verbose == 1:
            verbosity = logging.INFO
        else:
            verbosity = logging.DEBUG
        del options.verbose

        scraper = cls(verbosity=verbosity, **vars(options))

        scraper.write_metadata()

        years = options.years
        if options.all_years:
            years = [str(y) for y in range(scraper.earliest_year,
                                           datetime.datetime.now().year + 1)]
        if not years:
            parser.error(
                "You must provide a --year YYYY or --all (all years) option")

        chambers = []
        if options.upper:
            chambers.append('upper')
        if options.lower:
            chambers.append('lower')
        if not chambers:
            chambers = ['upper', 'lower']
        for year in years:
            try:
                if options.legislators:
                    for chamber in chambers:
                        scraper.scrape_legislators(chamber, year)
                for chamber in chambers:
                    scraper.old_bills = {}
                    scraper.scrape_bills(chamber, year)
            except NoDataForYear, e:
                if options.all_years:
                    pass
                else:
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
