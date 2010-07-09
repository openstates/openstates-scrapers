#!/usr/bin/env python
import datetime
import logging
from optparse import make_option, OptionParser
import os
import sys

from fiftystates.scrape import NoDataForPeriod, JSONDateEncoder

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

def main():
    def _run_scraper(scraper_type):
        """
            state: lower case two letter abbreviation of state
            scraper_type: bills, legislators, committees, votes
        """
        mod_path = 'fiftystates.scrape.%s.%s' % (state, scraper_type)
        scraper_name = '%s%sScraper' % (state.upper(), scraper_type[:-1].capitalize())

        try:
            mod = __import__(mod_path, fromlist=[scraper_name])
            ScraperClass = getattr(mod, scraper_name)
        except ImportError, e:
            if not options.alldata:
                raise RunException("could not import %s" % mod_path, e)
        except AttributeError, e:
            if not options.alldata:
                raise RunException("could not import %s" % scraper_name, e)

        scraper = ScraperClass(**opts)

        # times: the list to iterate over for second scrape param
        if years:
            times = years

        # run for sessions
        if scraper_type in ('bills', 'votes'):
            if not sessions:
                latest_session = metadata['terms'][-1]['sessions'][-1]
                print 'No session specified, using latest "%s"' % latest_session
                times = [latest_session]
            else:
                times = sessions
        elif scraper_type in ('legislators', 'committees'):
            if not terms:
                latest_term = metadata['terms'][-1]
                print 'No term specified using latest "%s"' % latest_term
                times = [latest_term]
            else:
                times = terms

        # run scraper against year/session/term
        for time in times:
            for chamber in chambers:
                scraper.scrape(chamber, time)


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
        make_option('--alldata', action='store_true', dest='alldata',
                    default=False, help="scrape all available types of data"),

        make_option('-v', '--verbose', action='count', dest='verbose',
                    default=False,
                    help="be verbose (use multiple times for more"\
                        "debugging information)"),
        make_option('-d', '--output_dir', action='store', dest='output_dir',
                    help='output directory'),
        make_option('-n', '--no_cache', action='store_true', dest='no_cache',
                    help="don't use web page cache"),
        make_option('-r', '--rpm', action='store', type="int", dest='rpm',
                    default=60),
    )

    parser = OptionParser(option_list=option_list)
    options, spares = parser.parse_args()

    if len(spares) != 1:
        raise RunException("Must pass a state abbreviation (eg. nc)")
    state = spares[0]

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

    # create output directories
    def makedir(path):
        try:
            os.makedirs(path)
        except OSError, e:
            if e.errno != 17 or os.path.isfile(path):
                raise e

    output_dir = options.output_dir or os.path.join('data', state)
    makedir(os.path.join(output_dir, "bills"))
    makedir(os.path.join(output_dir, "legislators"))
    makedir(os.path.join(output_dir, "committees"))

    # determine years
    years = options.years

    # determine sessions
    sessions = options.sessions
    terms = options.terms
    if terms:
        for term in metadata['terms']:
            if term in terms:
                sessions.extend(term['sessions'])
    sessions = set(sessions or [])

    if years:
        if sessions:
            raise RunException('cannot specify years and sessions')
        else:
            print 'use of -y, --years, --all is deprecated'
    else:
        years = []

    # determine chambers
    chambers = []
    if options.upper:
        chambers.append('upper')
    if options.lower:
        chambers.append('lower')
    if not chambers:
        chambers = ['upper', 'lower']

    if not (options.bills or options.legislators or options.votes or
            options.committees or options.alldata):
        raise RunException("Must specify at least one of --bills, --legislators, --committees, --votes")


    # write metadata
    try:
        metadata = __import__(state).metadata
        with open(os.path.join(output_dir, 'state_metadata.json'), 'w') as f:
            json.dump(metadata, f, cls=JSONDateEncoder)
    except (ImportError, AttributeError), e:
        pass

    opts = {'output_dir': output_dir,
            'no_cache': options.no_cache,
            'requests_per_minute': options.rpm,
            # cache_dir, error_dir
        }

    if options.alldata:
        options.bills = True
        options.legislators = True
        options.votes = True
        options.committees = True

    if options.bills:
        _run_scraper('bills')
    if options.legislators:
        _run_scraper('legislators')
    if options.committees:
        _run_scraper('committees')
    if options.votes:
        _run_scraper('votes')


if __name__ == '__main__':
    try:
        result = main()
    except RunException, e:
        print 'Error:', e
        sys.exit(1)
