#!/usr/bin/env python
import datetime
import glob
import logging
import os
import sys
import argparse
import json

from billy.conf import settings, base_arg_parser
from billy.scrape import (ScrapeError, NoDataForPeriod, JSONDateEncoder,
                          get_scraper)
from billy.scrape.validator import DatetimeValidator
from billy.importers.bills import import_bills

def _run_scraper(mod_path, state, options, metadata):
    """
        state: lower case two letter abbreviation of state
    """
    # make or clear directory for this type
    path = os.path.join(options.output_dir, 'bills')
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != 17:
            raise e
        else:
            for f in glob.glob(path+'/*.json'):
                os.remove(f)

    ScraperClass = get_scraper(mod_path, state, 'bills')

    opts = {'output_dir': options.output_dir,
            'no_cache': options.no_cache,
            'requests_per_minute': options.rpm,
            'strict_validation': options.strict,
            'retry_attempts': settings.SCRAPELIB_RETRY_ATTEMPTS,
            'retry_wait_seconds': settings.SCRAPELIB_RETRY_WAIT_SECONDS,
           }
    if options.fastmode:
        opts['requests_per_minute'] = 0
        opts['use_cache_first'] = True
    scraper = ScraperClass(metadata, **opts)

    print options.session, options.bill_id
    scraper.scrape_bill(options.session, options.bill_id)

def main():

    parser = argparse.ArgumentParser(
        description='Scrape data for state, saving data to disk.',
        parents=[base_arg_parser],
    )

    parser.add_argument('state', type=str,
                        help='state scraper module (eg. nc)')
    parser.add_argument('session', type=str,
                        help='session for bill to scrape')
    parser.add_argument('bill_id', type=str,
                        help='bill_id to scrape')
    parser.add_argument('--strict', action='store_true', dest='strict',
                        default=False, help="fail immediately when"
                        "encountering validation warning")
    parser.add_argument('-n', '--no_cache', action='store_true',
                        dest='no_cache', help="don't use web page cache")
    parser.add_argument('--fastmode', help="scrape in fast mode",
                        action="store_true", default=False)
    parser.add_argument('-r', '--rpm', action='store', type=int, dest='rpm',
                        default=60),
    parser.add_argument('--import', dest='do_import',
                        help="import bill after scrape",
                        action="store_true", default=False)

    args = parser.parse_args()

    settings.update(args)

    # set up search path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                    '../../openstates'))

    # get metadata
    metadata = __import__(args.state, fromlist=['metadata']).metadata
    state = metadata['abbreviation']

    # configure logger
    if args.verbose == 0:
        verbosity = logging.WARNING
    elif args.verbose == 1:
        verbosity = logging.INFO
    else:
        verbosity = logging.DEBUG

    logging.basicConfig(level=verbosity,
                        format="%(asctime)s %(name)s %(levelname)s " + state +
                               " %(message)s",
                        datefmt="%H:%M:%S",
                       )

    # make output dir
    args.output_dir = os.path.join(settings.BILLY_DATA_DIR, args.state)
    try:
        os.makedirs(args.output_dir)
    except OSError as e:
        if e.errno != 17:
            raise e

    _run_scraper(args.state, state, args, metadata)

    if args.do_import:
        import_bills(args.state, settings.BILLY_DATA_DIR)


if __name__ == '__main__':
    try:
        result = main()
    except ScrapeError as e:
        print 'Error:', e
        sys.exit(1)
