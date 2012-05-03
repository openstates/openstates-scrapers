import sys
import os
from os.path import dirname, abspath, join
import itertools
import json
import shutil
import urllib
import time
import datetime

import feedparser
import requests

import billy_settings
from billy.scrape import JSONDateEncoder

PATH = dirname(abspath(__file__))
DATA = billy_settings.DATA_DIR

request_defaults = {
    'proxies': {"http": "localhost:8001"},
    'timeout': 5.0,
    'headers': {
        'Accept': ('text/html,application/xhtml+xml,application/'
                   'xml;q=0.9,*/*;q=0.8'),
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-us,en;q=0.5',
        'Connection': 'keep-alive',
        'User-Agent': ('Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0.2) '
                       'Gecko/20100101 Firefox/10.0.2')
        },
    }

if __name__ == '__main__':

    session = requests.session(**request_defaults)

    def fetch(url):
        print url
        try:
            return session.get(url, **request_defaults)
        except Exception as e:
            print e

    filenames = os.listdir(join(PATH, 'urls'))
    filenames = filter(lambda s: '~' not in s, filenames)
    for urls_filename in filenames:
        abbr = urls_filename.lower().replace('.txt', '')
        with open(join(PATH, 'urls', urls_filename)) as urls:
            urls = urls.read().splitlines()
            urls = filter(lambda url: url.startswith('#'), urls)
            responses = filter(None, [fetch(url) for url in urls])
            #responses = requests.async.map(rs, size=4)

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

        for resp in responses:

            feed = feedparser.parse(resp.text)
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
                json.dump(feed['entries'], f, cls=JSONDateEncoder)
