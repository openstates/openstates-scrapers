#!/usr/bin/env python
import os
import sys
import argparse

from billy.conf import settings, base_arg_parser
from billy.scrape import ScrapeError, get_scraper
from billy.importers.bills import import_bills
from billy.utils import configure_logging
from billy.bin.scrape import _clear_scraped_data


def _run_scraper(options, metadata):
    _clear_scraped_data(options.output_dir, 'bills')

    ScraperClass = get_scraper(mod_path, 'bills')

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
    scraper.scrape_bill(options.chamber, options.session, options.bill_id)


def main():
    try:
        parser = argparse.ArgumentParser(
            description='Scrape data for single bill, saving data to disk.',
            parents=[base_arg_parser],
        )

        parser.add_argument('module', type=str, help='scraper module (eg. nc)')
        parser.add_argument('chamber', type=str,
                            help='chamber for bill to scrape')
        parser.add_argument('session', type=str,
                            help='session for bill to scrape')
        parser.add_argument('bill_id', type=str, help='bill_id to scrape')

        parser.add_argument('--strict', action='store_true', dest='strict',
                            default=False, help="fail immediately when"
                            "encountering validation warning")
        parser.add_argument('-n', '--no_cache', action='store_true',
                            dest='no_cache', help="don't use web page cache")
        parser.add_argument('--fastmode', help="scrape in fast mode",
                            action="store_true", default=False)
        parser.add_argument('-r', '--rpm', action='store', type=int,
                            dest='rpm', default=60),
        parser.add_argument('--import', dest='do_import',
                            help="import bill after scrape",
                            action="store_true", default=False)

        args = parser.parse_args()

        settings.update(args)

        # set up search path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                        '../../openstates'))

        # get metadata
        metadata = __import__(args.module, fromlist=['metadata']).metadata
        abbr = metadata['abbreviation']

        # configure logger
        configure_logging(args.verbose, abbr)

        args.output_dir = os.path.join(settings.BILLY_DATA_DIR, abbr)

        _run_scraper(args, metadata)

        if args.do_import:
            import_bills(abbr, settings.BILLY_DATA_DIR)
    except ScrapeError as e:
        print 'Error:', e
        sys.exit(1)


if __name__ == '__main__':
    main()
