import datetime
import logging
from optparse import make_option, OptionParser
from utils.legislation import NoDataForYear

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

        make_option('--bills', action='store_true', dest='legislators',
                    default=False, help="scrape bill data"),
        make_option('--legislators', action='store_true', dest='bills',
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
        make_option('-s', '--sleep', action='store_true', dest='sleep',
                    help="insert random delays wheen downloading web pages"),
    )

    parser = OptionParser(option_list=option_list)
    options, spares = parser.parse_args()

    if len(spares) != 1:
        print "Usage"
        return 1

    if options.verbose == 0:
        verbosity = logging.WARNING
    elif options.verbose == 1:
        verbosity = logging.INFO
    else:
        verbosity = logging.DEBUG

    # get scraper object
    state = spares[0]
    statemod = __import__('%s.get_legislation' % state)
    scraper = statemod.get_legislation.MDLegislationScraper(verbosity, vars(options))
    scraper.write_metadata()

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

    for year in years:
        #if matcher is None:
        #    scraper.reset_name_matchers()
        #else:
        #    scraper.reset_name_matchers(upper=matcher['upper'](),
        #                                lower=matcher['lower']())
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


if __name__ == '__main__':
    main()
