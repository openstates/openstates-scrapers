#!/usr/bin/env python
import datetime
import logging
from optparse import make_option, OptionParser
import os
import sys

from fiftystates.scrape import NoDataForYear, JSONDateEncoder

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

def run_oldschool(state, years, chambers, options):
    mod_name = "fiftystates.scrape.%s.get_legislation" % state
    scraper_name = '%sLegislationScraper' % state.upper()
    try:
        mod = __import__(mod_name, fromlist=[scraper_name])
        Scraper = getattr(mod, scraper_name)
    except ImportError:
        raise RunException("could not import %s" % mod_name)
    except AttributeError:
        raise RunException("could not import %sLegislationScraper"
                           % state.upper())

    scraper = Scraper(vars(options))

    scraper.write_metadata()

    for year in years:
        try:
            for chamber in chambers:
                if options.bills:
                    scraper.scrape_bills(chamber, year)
                if options.legislators:
                    scraper.scrape_legislators(chamber, year)
                if options.committees:
                    scraper.scrape_committees(chamber, year)
                if options.votes:
                    scraper.scrape_votes(chamber, year)
        except NoDataForYear, e:
            if options.all_years:
                pass
            else:
                raise

def _load_scraper(state, scraper_type):
    """
        state: lower case two letter abbreviation of state
        scraper_type: bills, legislators, committees, votes
    """
    mod_path = 'fiftystates.scrape.%s.%s' % (state, scraper_type)
    scraper_name = '%s%sScraper' % (state.upper(), scraper_type[:-1].capitalize())

    try:
        mod = __import__(mod_path, fromlist=[scraper_name])
        return getattr(mod, scraper_name)
    except ImportError, e:
        raise RunException("could not import %s" % mod_path, e)
    except AttributeError, e:
        raise RunException("could not import %s" % scraper_name, e)

def run(state, years, chambers, output_dir, options):

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

    # scrape bills
    if options.bills:
        BillScraper = _load_scraper(state, 'bills')
        scraper = BillScraper(**opts)
        for year in years:
            try:
                for chamber in chambers:
                    scraper.scrape(chamber, year)
            except NoDataForYear, e:
                if options.all_years:
                    pass
                else:
                    raise

    # scrape legislators
    if options.legislators:
        LegislatorScraper = _load_scraper(state, 'legislators')
        scraper = LegislatorScraper(**opts)
        for year in years:
            try:
                for chamber in chambers:
                    scraper.scrape(chamber, year)
            except NoDataForYear, e:
                pass

    # scrape committees
    if options.committees:
        CommitteeScraper = _load_scraper(state, 'committees')
        scraper = CommitteeScraper(**opts)
        for year in years:
            try:
                for chamber in chambers:
                    scraper.scrape(chamber, year)
            except NoDataForYear, e:
                pass

    # scrape votes
    if options.votes:
        VoteScraper = _load_scraper(state, 'votes')
        scraper = VoteScraper(**opts)
        for year in years:
            try:
                for chamber in chambers:
                    scraper.scrape(chamber, year)
            except NoDataForYear, e:
                pass


def main():
    option_list = (
        make_option('-y', '--year', action='append', dest='years',
                    help='year(s) to scrape'),
        make_option('--all', action='store_true', dest='all_years',
                    default=False, help='scrape all data (overrides --year)'),

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
        make_option('--old', action='store_true', dest='oldschool',
                    help="run an old style scraper"),
    )

    parser = OptionParser(option_list=option_list)
    options, spares = parser.parse_args()

    if len(spares) != 1:
        print "Must pass a state abbreviation (eg. nc)"
        return 1
    state = spares[0]

    # configure logger
    if options.verbose == 0:
        verbosity = logging.WARNING
    elif options.verbose == 1:
        verbosity = logging.INFO
    else:
        verbosity = logging.DEBUG

    logger = logging.getLogger("fiftystates")
    formatter = logging.Formatter("%(asctime)s %(levelname)s " + state +
                                  " %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    logger.setLevel(verbosity)

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
    if options.all_years:
        years = [str(y) for y in range(scraper.earliest_year,
                                       datetime.datetime.now().year + 1)]
    if not years:
        years = [datetime.datetime.now().year]

    # determine chambers
    chambers = []
    if options.upper:
        chambers.append('upper')
    if options.lower:
        chambers.append('lower')
    if not chambers:
        chambers = ['upper', 'lower']

    if not (options.bills or options.legislators or options.votes or
            options.committees):
        print "Must specify at least one of --bills, --legislators, --committees, --votes"
        return 1

    try:
        if options.oldschool:
            run_oldschool(state, years, chambers, options)
        else:
            run(state, years, chambers, output_dir, options)
    except RunException, e:
        print 'Error:', e
        return 1


if __name__ == '__main__':
    result = main()
    sys.exit(result)
