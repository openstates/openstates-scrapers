#!/usr/bin/env python
import glob
import logging
import os
import sys
import argparse
import json

from billy.conf import settings, base_arg_parser
from billy.scrape import ScrapeError, JSONDateEncoder, get_scraper
from billy.utils import configure_logging
from billy.scrape.validator import DatetimeValidator


def _clear_scraped_data(output_dir, scraper_type):
    # make or clear directory for this type
    path = os.path.join(output_dir, scraper_type)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != 17:
            raise e
        else:
            for f in glob.glob(path + '/*.json'):
                os.remove(f)


def _run_scraper(scraper_type, options, metadata):
    """
        scraper_type: bills, legislators, committees, votes
    """
    _clear_scraped_data(options.output_dir, scraper_type)
    mod_path = options.module

    try:
        ScraperClass = get_scraper(mod_path, scraper_type)
    except ScrapeError as e:
        # only re-raise if not alldata
        if not options.alldata:
            raise e
        else:
            return

    opts = {'output_dir': options.output_dir,
            'no_cache': options.no_cache,
            'requests_per_minute': options.rpm,
            'timeout': options.timeout,
            'strict_validation': options.strict,
            'retry_attempts': settings.SCRAPELIB_RETRY_ATTEMPTS,
            'retry_wait_seconds': settings.SCRAPELIB_RETRY_WAIT_SECONDS,
        }
    if options.fastmode:
        opts['requests_per_minute'] = 0
        opts['use_cache_first'] = True
    scraper = ScraperClass(metadata, **opts)

    # times: the list to iterate over for second scrape param
    if scraper_type in ('bills', 'votes', 'events'):
        if not options.sessions:
            if options.terms:
                times = []
                for term in options.terms:
                    scraper.validate_term(term)
                    for metaterm in metadata['terms']:
                        if term == metaterm['name']:
                            times.extend(metaterm['sessions'])
            else:
                latest_session = metadata['terms'][-1]['sessions'][-1]
                print('No session specified, using latest "%s"' %
                      latest_session)
                times = [latest_session]
        else:
            times = options.sessions

        # validate sessions
        for time in times:
            scraper.validate_session(time)
    elif scraper_type in ('legislators', 'committees'):
        if not options.terms:
            latest_term = metadata['terms'][-1]['name']
            print 'No term specified, using latest "%s"' % latest_term
            times = [latest_term]
        else:
            times = options.terms

        # validate terms
        for time in times:
            scraper.validate_term(time)

    # run scraper against year/session/term
    for time in times:
        for chamber in options.chambers:
            scraper.scrape(chamber, time)
        if scraper_type == 'events' and len(options.chambers) == 2:
            scraper.scrape('other', time)


def main():

    parser = argparse.ArgumentParser(
        description='Scrape legislative data, saving data to disk as JSON.',
        parents=[base_arg_parser],
    )

    parser.add_argument('module', type=str, help='scraper module (eg. nc)')
    parser.add_argument('-s', '--session', action='append', dest='sessions',
                        help='session(s) to scrape')
    parser.add_argument('-t', '--term', action='append', dest='terms',
                        help='term(s) to scrape')
    parser.add_argument('--upper', action='store_true', dest='upper',
                        default=False, help='scrape upper chamber')
    parser.add_argument('--lower', action='store_true', dest='lower',
                        default=False, help='scrape lower chamber')
    parser.add_argument('--bills', action='store_true', dest='bills',
                        default=False, help="scrape bill data")
    parser.add_argument('--legislators', action='store_true',
                        dest='legislators', default=False,
                        help="scrape legislator data")
    parser.add_argument('--committees', action='store_true', dest='committees',
                        default=False, help="scrape committee data")
    parser.add_argument('--votes', action='store_true', dest='votes',
                        default=False, help="scrape vote data")
    parser.add_argument('--events', action='store_true', dest='events',
                        default=False, help='scrape event data')
    parser.add_argument('--alldata', action='store_true', dest='alldata',
                        default=False,
                        help="scrape all available types of data")
    parser.add_argument('--strict', action='store_true', dest='strict',
                        default=False, help="fail immediately when"
                        "encountering validation warning")
    parser.add_argument('-n', '--no_cache', action='store_true',
                        dest='no_cache', help="don't use web page cache")
    parser.add_argument('--fastmode', help="scrape in fast mode",
                        action="store_true", default=False)
    parser.add_argument('-r', '--rpm', action='store', type=int, dest='rpm',
                        default=60)
    parser.add_argument('--timeout', action='store', type=int, dest='timeout',
                        default=10)

    args = parser.parse_args()

    settings.update(args)

    # set up search path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                    '../../openstates'))

    # get metadata
    metadata = __import__(args.module, fromlist=['metadata']).metadata

    configure_logging(args.verbose, args.module)

    # make output dir
    args.output_dir = os.path.join(settings.BILLY_DATA_DIR, args.module)
    try:
        os.makedirs(args.output_dir)
    except OSError as e:
        if e.errno != 17:
            raise e

    # write metadata
    try:
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/metadata.json')
        schema = json.load(open(schema_path))

        validator = DatetimeValidator()
        validator.validate(metadata, schema)
    except ValueError as e:
        logging.getLogger('billy').warning('metadata validation error: '
                                                 + str(e))

    with open(os.path.join(args.output_dir, 'state_metadata.json'), 'w') as f:
        json.dump(metadata, f, cls=JSONDateEncoder)

    # determine time period to run for
    if args.terms:
        for term in metadata['terms']:
            if term in args.terms:
                args.sessions.extend(term['sessions'])
    args.sessions = set(args.sessions or [])

    # determine chambers
    args.chambers = []
    if args.upper:
        args.chambers.append('upper')
    if args.lower:
        args.chambers.append('lower')
    if not args.chambers:
        args.chambers = ['upper', 'lower']

    if not (args.bills or args.legislators or args.votes or
            args.committees or args.events or args.alldata):
        raise ScrapeError("Must specify at least one of --bills, "
                          "--legislators, --committees, --votes, --events, "
                          "--alldata")

    if args.alldata:
        args.bills = True
        args.legislators = True
        args.votes = True
        args.committees = True

    if args.legislators:
        _run_scraper('legislators', args, metadata)
    if args.committees:
        _run_scraper('committees', args, metadata)
    if args.votes:
        _run_scraper('votes', args, metadata)
    if args.events:
        _run_scraper('events', args, metadata)
    if args.bills:
        _run_scraper('bills', args, metadata)


if __name__ == '__main__':
    try:
        result = main()
    except ScrapeError as e:
        print 'Error:', e
        sys.exit(1)
