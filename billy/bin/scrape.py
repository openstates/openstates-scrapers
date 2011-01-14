#!/usr/bin/env python
import datetime
import glob
import logging
import os
import sys
from optparse import make_option, OptionParser

from billy.scrape import (NoDataForPeriod, JSONDateEncoder,
                                _scraper_registry)
from billy.scrape.validator import DatetimeValidator

try:
    import json
except ImportError:
    import simplejson as json

class RunException(Exception):
    """ exception when trying to run a scraper """

    def __init__(self, msg, orig_exception=None):
        self.msg = msg
        self.orig_exception = orig_exception

    def __str__(self):
        if self.orig_exception:
            return '%s\nOriginal Exception: %s' % (self.msg, self.orig_exception)
        else:
            return self.msg

def _run_scraper(mod_path, state, scraper_type, options, metadata):
    """
        state: lower case two letter abbreviation of state
        scraper_type: bills, legislators, committees, votes
    """
    # make or clear directory for this type
    path = os.path.join(options.output_dir, scraper_type)
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != 17:
            raise e
        else:
            for f in glob.glob(path+'/*.json'):
                os.remove(f)

    try:
        mod_path = '%s.%s' % (mod_path, scraper_type)
        mod = __import__(mod_path)
    except ImportError, e:
        if not options.alldata:
            raise RunException("could not import %s" % mod_path, e)

    try:
        ScraperClass = _scraper_registry[state][scraper_type]
    except KeyError, e:
        if not options.alldata:
            raise RunException("no %s %s scraper found" %
                               (state, scraper_type))
        else:
            return

    opts = {'output_dir': options.output_dir,
            'no_cache': options.no_cache,
            'requests_per_minute': options.rpm,
            'strict_validation': options.strict,
            'retry_attempts': options.retries,
            'retry_wait_seconds': options.retry_wait,
            # TODO: cache_dir, error_dir?
        }
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
                print 'No session specified, using latest "%s"' % latest_session
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


def main():

    option_list = (
        make_option('-y', '--year', action='append', dest='years',
                    help='deprecated'),

        make_option('-s', '--session', action='append', dest='sessions',
                    help='session(s) to scrape'),
        make_option('-t', '--term', action='append', dest='terms',
                    help='term(s) to scrape'),

        make_option('--upper', action='store_true', dest='upper',
                    default=False, help='scrape upper chamber'),
        make_option('--lower', action='store_true', dest='lower',
                    default=False, help='scrape lower chamber'),

        make_option('--bills', action='store_true', dest='bills',
                    default=False, help="scrape bill data"),
        make_option('--legislators', action='store_true', dest='legislators',
                    default=False, help="scrape legislator data"),
        make_option('--committees', action='store_true', dest='committees',
                    default=False, help="scrape committee data"),
        make_option('--votes', action='store_true', dest='votes',
                    default=False, help="scrape vote data"),
        make_option('--events', action='store_true', dest='events',
                     default=False, help='scrape event data'),
        make_option('--alldata', action='store_true', dest='alldata',
                    default=False, help="scrape all available types of data"),

        make_option('-v', '--verbose', action='count', dest='verbose',
                    default=False,
                    help="be verbose (use multiple times for more"
                        "debugging information)"),
        make_option('--strict', action='store_true', dest='strict',
                    default=False, help="fail immediately when encountering a"
                        "validation warning"),
        make_option('-d', '--output_dir', action='store', dest='output_dir',
                    help='output directory'),
        make_option('-n', '--no_cache', action='store_true', dest='no_cache',
                    help="don't use web page cache"),
        make_option('-r', '--rpm', action='store', type="int", dest='rpm',
                    default=60),
        make_option('--retries', action='store', type="int", dest='retries',
                    default=3),
        make_option('--retry_wait', action='store', type="int",
                    dest='retry_wait', default=10),
    )

    parser = OptionParser(option_list=option_list)
    options, spares = parser.parse_args()

    # loading from module
    if len(spares) != 1:
        raise RunException("Must pass a path to a metadata module (eg. nc)")
    mod_name = spares[0]

    # set up search path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                    '../../openstates'))

    metadata = __import__(mod_name, fromlist=['metadata']).metadata
    state = metadata['abbreviation']

    # configure logger
    if options.verbose == 0:
        verbosity = logging.WARNING
    elif options.verbose == 1:
        verbosity = logging.INFO
    else:
        verbosity = logging.DEBUG

    logging.basicConfig(level=verbosity,
                        format="%(asctime)s %(name)s %(levelname)s " + state +
                               " %(message)s",
                        datefmt="%H:%M:%S",
                       )

    # make output dir if it doesn't exist
    options.output_dir = options.output_dir or os.path.join('data', state)
    try:
        os.makedirs(options.output_dir)
    except OSError, e:
        if e.errno != 17:
            raise e

    # write metadata
    try:
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/metadata.json')
        schema = json.load(open(schema_path))

        validator = DatetimeValidator()
        validator.validate(metadata, schema)
    except ValueError, e:
        logging.getLogger('billy').warning('metadata validation error: '
                                                 + str(e))

    with open(os.path.join(options.output_dir, 'state_metadata.json'), 'w') as f:
        json.dump(metadata, f, cls=JSONDateEncoder)

    # determine time period to run for
    if options.terms:
        for term in metadata['terms']:
            if term in options.terms:
                options.sessions.extend(term['sessions'])
    options.sessions = set(options.sessions or [])

    if options.years:
        raise RunException('use of --years is no longer supported')

    # determine chambers
    chambers = []
    if options.upper:
        chambers.append('upper')
    if options.lower:
        chambers.append('lower')
    if not chambers:
        chambers = ['upper', 'lower']
    options.chambers = chambers

    if not (options.bills or options.legislators or options.votes or
            options.committees or options.events or options.alldata):
        raise RunException("Must specify at least one of --bills, "
                           "--legislators, --committees, --votes, --events, "
                           "--alldata")

    if options.alldata:
        options.bills = True
        options.legislators = True
        options.votes = True
        options.committees = True

    if options.bills:
        _run_scraper(mod_name, state, 'bills', options, metadata)
    if options.legislators:
        _run_scraper(mod_name, state, 'legislators', options, metadata)
    if options.committees:
        _run_scraper(mod_name, state, 'committees', options, metadata)
    if options.votes:
        _run_scraper(mod_name, state, 'votes', options, metadata)
    if options.events:
        _run_scraper(mod_name, state, 'events', options, metadata)


if __name__ == '__main__':
    try:
        result = main()
    except RunException, e:
        print 'Error:', e
        sys.exit(1)
