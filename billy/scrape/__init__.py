import os
import time
import logging
import datetime
import json
from collections import defaultdict

from billy.scrape.validator import DatetimeValidator

from billy.conf import settings

import scrapelib


class ScrapeError(Exception):
    """
    Base class for scrape errors.
    """
    def __init__(self, msg, orig_exception=None):
        self.msg = msg
        self.orig_exception = orig_exception

    def __str__(self):
        if self.orig_exception:
            return '%s\nOriginal Exception: %s' % (self.msg,
                                        self.orig_exception)
        else:
            return self.msg


class NoDataForPeriod(ScrapeError):
    """
    Exception to be raised when no data exists for a given period
    """
    def __init__(self, period):
        self.period = period

    def __str__(self):
        return 'No data exists for %s' % self.period


class JSONDateEncoder(json.JSONEncoder):
    """
    JSONEncoder that encodes datetime objects as Unix timestamps.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return time.mktime(obj.utctimetuple())
        elif isinstance(obj, datetime.date):
            return time.mktime(obj.timetuple())

        return json.JSONEncoder.default(self, obj)

# maps scraper_type -> scraper
_scraper_registry = dict()

class ScraperMeta(type):
    """ register derived scrapers in a central registry """

    def __new__(meta, classname, bases, classdict):
        cls = type.__new__(meta, classname, bases, classdict)

        # default level to state to preserve old behavior
        if not hasattr(cls, 'level'):
            cls.level = 'state'
            cls.country = 'us'

        region = getattr(cls, cls.level, None)
        scraper_type = getattr(cls, 'scraper_type', None)

        if region and scraper_type:
            _scraper_registry[scraper_type] = cls

        return cls


class Scraper(scrapelib.Scraper):
    """ Base class for all Scrapers

    Provides several useful methods for retrieving URLs and checking
    arguments against metadata.
    """

    __metaclass__ = ScraperMeta

    def __init__(self, metadata, no_cache=False, output_dir=None,
                 strict_validation=None, **kwargs):
        """
        Create a new Scraper instance.

        :param metadata: metadata for this scraper
        :param no_cache: if True, will ignore any cached downloads
        :param output_dir: the data directory to use
        :param strict_validation: exit immediately if validation fails
        """

        # configure underlying scrapelib object
        if no_cache:
            kwargs['cache_dir'] = None
        elif 'cache_dir' not in kwargs:
            kwargs['cache_dir'] = settings.BILLY_CACHE_DIR

        if 'error_dir' not in kwargs:
            kwargs['error_dir'] = settings.BILLY_ERROR_DIR

        if 'timeout' not in kwargs:
            kwargs['timeout'] = settings.SCRAPELIB_TIMEOUT

        if 'requests_per_minute' not in kwargs:
            kwargs['requests_per_minute'] = None

        if 'retry_attempts' not in kwargs:
            kwargs['retry_attempts'] = settings.SCRAPELIB_RETRY_ATTEMPTS

        if 'retry_wait_seconds' not in kwargs:
            kwargs['retry_wait_seconds'] = \
                    settings.SCRAPELIB_RETRY_WAIT_SECONDS

        super(Scraper, self).__init__(**kwargs)

        for f in settings.BILLY_LEVEL_FIELDS[self.level]:
            if not hasattr(self, f):
                raise Exception('%s scrapers must have a %s attribute' % (
                    self.level, f))

        self.metadata = metadata
        self.output_dir = output_dir

        # make output dir, error dir, and cache dir
        for d in (self.output_dir, kwargs['cache_dir'], kwargs['error_dir']):
            try:
                if d:
                    os.makedirs(d)
            except OSError as e:
                if e.errno != 17:
                    raise e

        # validation
        self.strict_validation = strict_validation
        self.validator = DatetimeValidator()

        self.follow_robots = False

        # logging convenience methods
        self.logger = logging.getLogger("billy")
        self.log = self.logger.info
        self.debug = self.logger.debug
        self.warning = self.logger.warning

    def validate_json(self, obj):
        if not hasattr(self, '_schema'):
            self._schema = self._get_schema()
        try:
            self.validator.validate(obj, self._schema)
        except ValueError as ve:
            self.warning(str(ve))
            if self.strict_validation:
                raise ve

    def all_sessions(self):
        sessions = []
        for t in self.metadata['terms']:
            sessions.extend(t['sessions'])
        return sessions

    def validate_session(self, session):
        """ Check that a session is present in the metadata dictionary.

        raises :exc:`~billy.scrape.NoDataForPeriod` if session is invalid

        :param session:  string representing session to check
        """
        for t in self.metadata['terms']:
            if session in t['sessions']:
                return True
        raise NoDataForPeriod(session)

    def validate_term(self, term, latest_only=False):
        """ Check that a term is present in the metadata dictionary.

        raises :exc:`~billy.scrape.NoDataForPeriod` if term is invalid

        :param term:        string representing term to check
        :param latest_only: if True, will raise exception if term is not
                            the current term (default: False)
        """

        if latest_only:
            if term == self.metadata['terms'][-1]['name']:
                return True
            else:
                raise NoDataForPeriod(term)

        for t in self.metadata['terms']:
            if term == t['name']:
                return True
        raise NoDataForPeriod(term)

    def save_object(self, obj):
        # copy over level information
        obj['level'] = self.level
        for f in settings.BILLY_LEVEL_FIELDS[self.level]:
            obj[f] = getattr(self, f)

        filename = obj.get_filename()
        with open(os.path.join(self.output_dir, self.scraper_type, filename),
                  'w') as f:
            json.dump(obj, f, cls=JSONDateEncoder)

        # validate after writing, allows for inspection
        self.validate_json(obj)

class SourcedObject(dict):
    """ Base object used for data storage.

    Base class for :class:`~billy.scrape.bills.Bill`,
    :class:`~billy.scrape.legislators.Legislator`,
    :class:`~billy.scrape.votes.Vote`,
    and :class:`~billy.scrape.committees.Committee`.

    SourcedObjects work like a dictionary.  It is possible
    to add extra data beyond the required fields by assigning to the
    `SourcedObject` instance like a dictionary.
    """

    def __init__(self, _type, **kwargs):
        super(SourcedObject, self).__init__()
        self['_type'] = _type
        self['sources'] = []
        self.update(kwargs)

    def add_source(self, url, **kwargs):
        """
        Add a source URL from which data related to this object was scraped.

        :param url: the location of the source
        """
        self['sources'].append(dict(url=url, **kwargs))


def get_scraper(mod_path, scraper_type):
    """ import a scraper from the scraper registry """

    # act of importing puts it into the registry
    try:
        mod_path = '%s.%s' % (mod_path, scraper_type)
        __import__(mod_path)
    except ImportError as e:
        raise ScrapeError("could not import %s" % mod_path, e)

    # now pull the class out of the registry
    try:
        ScraperClass = _scraper_registry[scraper_type]
    except KeyError as e:
        raise ScrapeError("no %s scraper found in module %s" %
                           (scraper_type, mod_path))
    return ScraperClass
