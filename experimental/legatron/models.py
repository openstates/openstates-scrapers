'''The basic problem this rewrite tries to address is a lack of good reporting
on what happens during each scrape. It would be useful to know how many new
entries with relevant entities were seen on each scrape, which feeds never
have useful entries, which states or particular legislators don't have many
entries, etc. These things will help in curating and debugging the news feed
scraping so we can figure out whether some states need more links or more
specific patterns added to identify bills, committees, legislators.
'''
import time
import datetime
import traceback
import hashlib

import feedparser

import scrapelib
from billy.core import logging
from billy.core import feeds_db


USER_AGENT = ('Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0.2) '
              'Gecko/20100101 Firefox/10.0.2')
FASTMODE = True


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
        requests_per_minute=0,
        cache_write_only=False)

    session = scrapelib.Scraper(**_request_defaults(request_defaults))
    logger = logging.getLogger('billy.feed-model')

    def __init__(self, url):
        self.url = url
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
            # are scanned for multiple jursidictions. For example:
            'ex': self.default_report
            }

        # Delete example data.
        self.report['ex']

        self._initial_save()

    def _initial_save(self):
        '''Perform the initial save (to get us the mongo_id if none exists yet.
        '''
        spec = dict(url=self.url)
        update = {'$set': spec}
        self.logger.info('feed._initial_save %r' % self.url)
        doc = feeds_db.feeds.find_and_modify(spec, update, upsert=True)
        self.mongo_id = doc['_id']

    def _get_feed(self):
        '''Try to fetch the feed and parse it. If the fetch fails, log
        the exception. Finally, update the report with details of the
        success/failure of the fetch.
        '''
        self.logger.info('feed GET %r' % self.url)
        try:
            text = self.session.get(self.url).text
        except Exception:
            tb = traceback.format_exc()
            self._handle_fetch_exception(tb)
            return

        self.succeeded = True

        # XXX: This will fail if the link doesn't point to a valid feed.
        data = feedparser.parse(text)
        self._data = data

        self._update_report_after_fetch()
        return data

    @property
    def data(self):
        '''The parsed feed contents.
        '''
        data = getattr(self, '_data', None)
        return data or self._get_feed()

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
        report = {
            'url': self.url,
            'last_fetch': last_fetch
            }
        self.report.update(report)

    def entries(self):
        '''A generator of wrapped entries for this feed.
        '''
        for entry in self.data['entries']:
            yield Entry(entry, feed=self)

    def serializable(self):
        '''Returns metadata about the feed (url, etc) and report information
        that can be saved in mongo.
        '''
        return {'$set': self.report}

    def finish_report(self):
        '''
        '''

    def save(self):
        '''
        '''
        spec = dict(url=self.url)
        feeds_db.feeds.find_and_modify(spec, self.serializable(), upsert=True)
        self.logger.info('feed.save: %r' % self.url)


class Entry(object):
    '''Wrap a parsed feed entry dictionary thingy from feedparser.
    '''
    request_defaults = dict(
        requests_per_minute=0,
        cache_write_only=False)

    session = scrapelib.Scraper(**_request_defaults(request_defaults))
    logger = logging.getLogger('billy.entry-model')

    def __init__(self, entry, feed):
        self.entry = entry
        self.feed = feed
        self.report = {}

        # Whether a fetch of the full text was tried and succeeded.
        self.tried = False
        self.succeeded = None

    def mongo_id(self):
        '''Get a unique mongo id based on this entry's url and title.
        '''
        s = self.entry['link'] + self.entry['title']
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
        self.logger.info('is_new? %r --> %r' % (mongo_id, is_new))

    def _get_full_text(self):
        '''Just for experimenting at this point. Fetch the full text,
        log any exception the occurs, and store the details regarding the
        outcome of the fetch on the object.
        '''
        self.logger.info('entry GET %r' % self.entry.link)
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
        ret = dict(feed_id=self.feed.mongo_id)

        # Convert unserializable timestructs into datetimes.
        for k, v in self.entry.items():
            if isinstance(v, time.struct_time):
                t = time.mktime(self.entry[k])
                dt = datetime.datetime.fromtimestamp(t)
                ret[k] = dt
        return ret

    def save_if_entities_found(self):
        '''If the entry is previously unseen and the extractor finds entities
        have been mentioned, save, otherwise do nothing.
        '''
        if self.is_new() and self.entry['entity_ids']:
            feeds_db.entries.save(self.serializable())
            self.logger('entry.save_if_entities_found: %r' % self.entry.link)

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
        if self.tried:
            report['entries']['new'] += 1
            if self.entry['entity_ids']:
                report['entries']['relevant'] += 1
            report['entities']['count'] += len(self.entry['entity_ids'])
        else:
            report['entries']['old'] += 1






