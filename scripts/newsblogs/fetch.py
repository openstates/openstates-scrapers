import sys
import os
from os.path import dirname, abspath, join
import itertools
import json
import shutil

import feedparser
import requests
import requests.async

from billy.conf import settings

PATH = dirname(abspath(__file__))
DATA = settings.BILLY_DATA_DIR

request_defaults = {
    'proxies': {"http": "localhost:8001"},
    #'cookies': cookielib.LWPCookieJar(join(PATH, 'cookies.lwp')),
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

	states = sys.argv[1:]
	session = requests.Session(**request_defaults)

	def fetch(url):
		try:
			return requests.get(url, **request_defaults)
		except Exception as e:
			print e

	for abbr in states:
		abbr = abbr.lower()
		with open(join(PATH, 'urls', '%s.txt' % abbr)) as urls:
			urls = urls.read().splitlines()
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
				os.mkdir(folder)
			except OSError:
				pass

		for resp in responses:
			fn = join(STATE_DATA_RAW, resp.url.replace('/', ','))
			with open(fn, 'w') as f:
				f.write(resp.text.encode('utf8'))
