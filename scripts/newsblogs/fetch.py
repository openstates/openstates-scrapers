import os
import sys
from os.path import dirname, abspath, join
import json
import shutil
import time
import datetime
import logging
import socket

import feedparser

import scrapelib
from billy.utils import JSONEncoderPlus


PATH = dirname(abspath(__file__))
DATA = 'data'

logger = logging.getLogger('newsblogs.fetch')
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(message)s',
                              datefmt='%H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)


if __name__ == '__main__':

    session = scrapelib.Scraper()
    session.headers = {
        'Accept': ('text/html,application/xhtml+xml,application/'
                   'xml;q=0.9,*/*;q=0.8'),
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-us,en;q=0.5',
        'Connection': 'keep-alive',
        }
    session.user_agent = (
        'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0.2) '
        'Gecko/20100101 Firefox/10.0.2')
    session.timeout = 15.0
    session.follow_robots = False

    def fetch(url):
        logger.info('trying %r' % url)
        try:
            return session.get(url)
        except Exception as e:
            logger.exception(e)

    filenames = os.listdir(join(PATH, 'urls'))
    filenames = filter(lambda s: '~' not in s, filenames)
    for urls_filename in filenames:
        abbr = urls_filename.lower().replace('.txt', '')
        if sys.argv[1:] and (abbr not in sys.argv[1:]):
            continue
        with open(join(PATH, 'urls', urls_filename)) as urls:
            urls = urls.read().splitlines()
            ignored = lambda url: not url.strip().startswith('#')
            urls = filter(ignored, urls)
            responses = filter(None, urls)

        STATE_DATA = join(DATA, abbr, 'feeds')
        STATE_DATA_RAW = join(STATE_DATA, 'raw')

        try:
            shutil.rmtree(STATE_DATA_RAW)
        except OSError:
            pass

        for folder in (STATE_DATA, STATE_DATA_RAW):
            try:
                os.makedirs(folder)
            except OSError:
                pass

        for url in urls:

            resp = fetch(url)
            if not resp:
                continue

            try:
                text = resp.text
            except Exception as e:
                logger.exception(e)
                continue

            feed = feedparser.parse(text)
            for entry in feed['entries']:
                # inbox_url = ('https://inbox.influenceexplorer.com/'
                #              'contextualize?apikey=%s&text="%s"')

                # try:
                #     text = entry['summary'].encode('utf-8')
                # except KeyError:
                #     text = entry['title'].encode('utf-8')
                # search_text = urllib.quote(text)
                # inbox_url = inbox_url % (billy_settings.settings.SUNLIGHT_API_KEY,
                #                          search_text)

                # resp2 = session.get(inbox_url)
                # try:
                #     inbox_data = json.loads(resp2.text)
                # except ValueError:
                #     pass
                # else:
                #     entry['_inbox_data'] = inbox_data

                # Patch the entry object to get rid of struct_time.
                for k, v in entry.items():
                    if isinstance(v, time.struct_time):
                        t = time.mktime(entry[k])
                        dt = datetime.datetime.fromtimestamp(t)
                        entry[k] = dt

            fn = join(STATE_DATA_RAW, resp.url.replace('/', ','))
            with open(fn, 'w') as f:
                json.dump(feed['entries'], f, cls=JSONEncoderPlus)
