from optparse import make_option, OptionParser
import datetime
import csv

class NoDataForYear(Exception):
    """ exception to be raised when no data exists for a given year """

    def __init__(self, year):
        self.year = year

    def __str__(self):
        return 'No data exists for %s' % year

def run_legislation_scraper(get_bills_func):
    option_list = (
        make_option('-y', '--year', action='append', dest='years',
                    help='year(s) to scrape'),
        make_option('--all', action='store_true', dest='all_years',
                    default=False, help='scrape all data (overrides --year)'),
        make_option('--upper', action='store_true', dest='upper', default=False,
                    help='scrape upper chamber'),
        make_option('--lower', action='store_true', dest='lower', default=False,
                    help='scrape lower chamber'),
    )

    options, spares = OptionParser(option_list=option_list).parse_args()
    years = options.years
    if options.all_years:
        years = [str(y) for y in range(1969, datetime.datetime.now().year+1)]
    chambers = []
    if options.upper:
        chambers.append('upper')
    if options.lower:
        chambers.append('lower')
    if not chambers:
        chambers = ['upper', 'lower']
    fields = ('state', 'chamber', 'session', 'bill_id', 'remote_url')
    output = csv.DictWriter(open('output.csv', 'w'), fields)

    for chamber in chambers:
        for year in years:
            try:
                for bill in get_bills_func(chamber, year):
                    output.writerow(bill)
            except NoDataForYear, e:
                if options.all_years:
                    pass
                else:
                    raise

