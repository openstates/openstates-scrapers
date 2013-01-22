'''The basic problem this rewrite tries to address is a lack of good reporting
on what happens during each scrape. It would be useful to know how many new
entries with relevant entities were seen on each scrape, which feeds never
have useful entries, which states or particular legislators don't have many
entries, etc. These things will help in curating and debugging the news feed
scraping so we can figure out whether some states need more links or more
specific patterns added to identify bills, committees, legislators.

Note: Script needs to blast the feed cache at the beginning of each run.

'''
import time
import datetime
import traceback
import hashlib
import shutil

import feedparser

import scrapelib
from scrapelib.cache import FileCache
from billy.core import logging
from billy.core import feeds_db


USER_AGENT = ('Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0.2) '
              'Gecko/20100101 Firefox/10.0.2')

FASTMODE = True

# This assumes the script will be run with openstates as the cwd.
FEEDS_CACHE = 'cache/feeds'
ENTRIES_CACHE = 'cache/entries'


def _request_defaults(kwargs):
    '''Return defaults for a requests session.
    '''
    request_defaults = {
        #'proxies': {"http": "localhost:8001"},
        'timeout': 5.0,
        'headers': {
            'Accept': ('text/html,application/xhtml+xml,application/'
                       'xml;q=0.9,*/*;q=0.8'),
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-us,en;q=0.5',
            'Connection': 'keep-alive',
            },
        'user_agent': USER_AGENT,
        'follow_robots': False,
        }
    request_defaults.update(kwargs)
    return request_defaults


class Feed(object):
    '''This model handles fetching the rss feed and recording any errors
    that occur for post-mortem reporting. It also has an instance-level
    report dictionary that gets augmented each time one of the feed's
    entries is scanned for relevant entities.
    '''

    request_defaults = dict(
        cache_obj=FileCache(FEEDS_CACHE),
        requests_per_minute=0,
        cache_write_only=False)

    session = scrapelib.Scraper(
        **_request_defaults(request_defaults))
    logger = logging.getLogger('billy.feed-model')

    def __init__(self, url, jurisdiction):
        self.url = url
        self.jurisdiction = jurisdiction

        self.succeeded = None
        self.default_report = {
            'entries': {
                'count': 0,
                'new': 0,
                'old': 0,
                'relevant': 0,
                },
            'entities': {
                'count' : 0,
                }
            }
        self.report = {
            'url': url,

            # The info is stored under the jurisdiction key
            # to avoid over-writing data for feeds with national scope that
            # are scanned for multiple jursidictions.
            jurisdiction: self.default_report
            }


        # Make sure this feed has a mongo id.
        self._initial_save()

    @staticmethod
    def blast_cache(self):
        '''Remove the scrapelib.Scraper fastmode cache for feed retrieval.
        Done before a scrape, but not before multiple jurisdictions in a
        single run, in case a feed of national scope needs to get processed
        for each state.
        '''
        shutil.rmtree(FEEDS_CACHE)

    def _initial_save(self):
        '''Perform the initial save (to get us the mongo_id if none exists yet.
        '''
        spec = dict(url=self.url)
        update = {'$set': spec}
        self.logger.debug('feed._initial_save %r' % self.url)
        doc = feeds_db.feeds.find_and_modify(
            spec, update, upsert=True, new=True)
        self.mongo_id = doc['_id']

    def _get_feed(self):
        '''Try to fetch the feed and parse it. If the fetch fails, log
        the exception. Finally, update the report with details of the
        success/failure of the fetch.
        '''
        try:
            text = self.session.get(self.url).text
        except Exception:
            tb = traceback.format_exc()
            self._handle_fetch_exception(tb)
            self._update_report_after_fetch()
        else:
            self.succeeded = True

            # XXX: This will fail if the text isn't a valid feed.
            data = feedparser.parse(text)
            self._data = data
            self._update_report_after_fetch()
            return data

    @property
    def data(self):
        '''The parsed feed contents.
        '''
        data = getattr(self, '_data', None)
        return data or self._get_feed() or {}

    def is_valid(self):
        '''Does this hot garbage contain the keys we expect?
        '''
        return 'title' in self.data.get('feed', {})

    def _handle_fetch_exception(self, _traceback):
        '''If the fetch fails, log the exception and store the traceback for
        the report.
        '''
        self.traceback = _traceback
        self.logger.exception(_traceback)
        self.succeeded = False

    def _update_report_after_fetch(self):
        '''Update the feed's report with whether the fetch operation
        succeeded or failed, including a formatted traceback if it failed.
        '''
        last_fetch = {
            'succeeded': self.succeeded,
            'datetime': datetime.datetime.utcnow()
            }
        if not self.succeeded:
            last_fetch['traceback'] = self.traceback
        self.report[self.jurisdiction].update(last_fetch=last_fetch)

    def entries(self):
        '''A generator of wrapped entries for this feed.
        '''
        data = self.data or {}
        entries = data.get('entries', [])
        for entry in entries:
            yield Entry(entry, feed=self)

    def serializable(self):
        '''Returns metadata about the feed (url, etc) and report information
        that can be saved in mongo.
        '''
        return {'$set': self.report}

    def finish_report(self):
        '''Extra stuff to go in the report goes here.
        '''

    def save(self):
        '''Update the feed record with the latest report.
        '''
        if not self.is_valid():
            return
        spec = dict(url=self.url)
        update = {'$set': self.report}
        self.logger.debug('feed.finish_report %r' % self.url)
        feeds_db.feeds.find_and_modify(spec, update, upsert=True, new=True)
        self.logger.info('feed.save: %r' % self.url)


class Entry(object):
    '''Wrap a parsed feed entry dictionary thingy from feedparser.
    '''
    request_defaults = dict(
        cache_obj=FileCache(ENTRIES_CACHE),
        requests_per_minute=0,
        cache_write_only=False)

    session = scrapelib.Scraper(**_request_defaults(request_defaults))
    logger = logging.getLogger('billy.entry-model')

    def __init__(self, entry, feed):
        self.entry = entry
        self.feed = feed
        self.report = {
            'entities': {
                'count' : 0,
                }
            }

        # Whether a fetch of the full text was tried and succeeded.
        self.tried = False
        self.succeeded = None

    def is_valid(self):
        '''Does this hot garbage contain the keys we expect?
        '''
        valid = set(['summary', 'link', 'title'])
        return valid < set(self.entry)

    @staticmethod
    def blast_cache(self):
        '''Just in case you want to blast the entries cache.
        '''
        shutil.rmtree(ENTRIES_CACHE)

    def mongo_id(self):
        '''Get a unique mongo id based on this entry's url and title.
        '''
        s = self.entry['link'] + self.entry['title']
        s = s.encode('ascii', 'ignore')
        return hashlib.md5(s).hexdigest()

    def is_new(self):
        '''Guess whether this entry is new (i.e., previously unseen)
        or old.
        '''
        mongo_id = self.mongo_id()
        if feeds_db.entries.find_one(mongo_id) is None:
            is_new = True
        else:
            is_new = False
        self.logger.debug('is_new? %r --> %r' % (mongo_id, is_new))
        return is_new

    def _get_full_text(self):
        '''Just for experimenting at this point. Fetch the full text,
        log any exception the occurs, and store the details regarding the
        outcome of the fetch on the object.
        '''
        self.logger.debug('entry GET %r' % self.entry.link)
        try:
            html = self.session.get(self.entry.link).text
        except Exception:
            tb = traceback.format_exc()
            self._handle_fetch_exception(tb)
            return

        self.succeeded = True
        self.tried = True
        self.html = html

        self._update_report_after_fetch()

        return html

    def _handle_fetch_exception(self, _traceback):
        '''If the fetch failed, log the failre and store the traceback
        object for the report.
        '''
        self.traceback = _traceback
        self.logger.exception(_traceback)
        self.succeeded = False

    def _update_report_after_fetch(self):
        '''After fetching the entry's full text (if at all), update
        the entry's report with the outcome of the fetch operation, including
        a traceback if it failed.
        '''
        report = {
            'url': self.url,
            'entity_count': len(self['entity_ids'])
            }

        if self.tried:
            last_fetch = {
                'succeeded': self.succeeded,
                'datetime': datetime.datetime.utcnow()
                }
            if not self.succeeded:
                last_fetch['traceback'] = self.traceback
            report.update(last_fetch=last_fetch)
        self.report.update(report)

    def serializable(self):
        '''Replace date objects with datetime objects that can be
        json serialized.
        '''
        # Add the feed's id to make the entry and its feed joinable.
        ret = {}
        ret['feed_id'] = self.feed.mongo_id

        # Convert unserializable timestructs into datetimes.
        for k, v in self.entry.items():
            if isinstance(v, time.struct_time):
                t = time.mktime(self.entry[k])
                dt = datetime.datetime.fromtimestamp(t)
                ret[k] = dt
            elif '.' not in k:
                ret[k] = v

        return ret

    def save_if_entities_found(self):
        '''If the entry is previously unseen and the extractor finds entities
        have been mentioned, save, otherwise do nothing.
        '''
        if self.is_valid() and self.is_new() and self.entry['entity_ids']:
            feeds_db.entries.save(self.serializable())
            msg = 'found %d entities: %r'
            args = (len(self.entry['entity_ids']), self.entry.link)
            self.logger.debug(msg % args)

    def finish_report(self, abbr):
        '''After attempting to extract entities, update the report and the
        report of this entry's feed with relevant information.

        Two things happen in this function: the entry's report gets updated,
        and the report object on the entry's feed gets updated.

        The feed's default report for a jurisdiction has this basic shape:
            {
            'entries': {
                'count': 0,
                'new': 0,
                'old': 0,
                'relevant': 0,
                },
            'entities': {
                'count' : 0,
                }
            }

        `abbr` is the jurisdiction abbreviation this info will be stored under
        in the feed's report object.
        '''
        # Update the feed's report.
        feed_report = self.feed.report
        report = feed_report.get(abbr, self.feed.default_report)

        report['entries']['count'] += 1

        # If this is a new entry...
        if self.is_new():
            report['entries']['new'] += 1
            if self.entry['entity_ids']:
                report['entries']['relevant'] += 1
            report['entities']['count'] += len(self.entry['entity_ids'])
            self.report['entities']['count'] += len(self.entry['entity_ids'])
        else:
            report['entries']['old'] += 1
