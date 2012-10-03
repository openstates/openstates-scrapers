'''
Given a state as the first parameter, this module tries to
fetch bill text for all the state's bills and store them
in settings.BILLY_DATA_DIR. Scrapelib caching is on.
'''
import sys
import os
from os.path import join

from billy import db
from billy.conf import settings
import scrapelib

import logbook


def main(abbr):

    request_defaults = {
        # 'proxies': {"http": "localhost:8888"},
        'timeout': 5.0,
        'headers': {
            'Accept': ('text/html,application/xhtml+xml,application/'
                       'xml;q=0.9,*/*;q=0.8'),
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-us,en;q=0.5',
            'User-Agent': ('Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0.2) '
                           'Gecko/20100101 Firefox/10.0.2'),
            },
        'follow_robots': False,

        # Note, this script needs run in the same dir as billy_settings.py
        }

    logger = logbook.Logger()
    DATA = join(settings.BILLY_DATA_DIR, abbr, 'billtext')

    try:
        os.makedirs(DATA)
    except OSError:
        pass
    logger.info('writing files to %r' % DATA)

    session = scrapelib.Scraper(
        cache_obj=scrapelib.FileCache('cache'),
        cache_write_only=False,
        use_cache_first=True,
        requests_per_minute=0,
        **request_defaults)

    for bill in db.bills.find({'state': abbr}):
        if len(bill['versions']):
            bill_id = bill['bill_id']
            url = bill['versions'][0]['url']
            logger.info('trying %r: %r' % (bill_id, url))
            text = session.get(url).text
            with open(join(DATA, bill['_id']), 'w') as f:
                f.write(text.encode('utf-8'))


if __name__ == '__main__':
    main(sys.argv[1])
