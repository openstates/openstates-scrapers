from optparse import make_option, OptionParser
import csv

def run_legislation_scraper(get_bills_func):
    option_list = (
        make_option('-y', '--year', action='append', dest='years', 
                    help='year(s) to scrape'),
        make_option('--upper', action='store_true', dest='upper', default=False,
                    help='scrape upper chamber'),
        make_option('--lower', action='store_true', dest='lower', default=False,
                    help='scrape lower chamber'),
        make_option('--download', action='store_true', dest='download', 
                    default=False, help='store bills locally'),
    )

    options, spares = OptionParser(option_list=option_list).parse_args()
    years = options.years
    chambers = []
    if options.upper:
        chambers.append('upper')
    if options.lower:
        chambers.append('lower')
    download = options.download
    fields = ('state', 'chamber', 'session', 'bill_id', 'remote_url')
    output = csv.DictWriter(open('output.csv', 'w'), fields)

    #all_funcs = chain(*[get_bills_func(chamber, year)
    #                    for year in years for chamber in chambers])
    #saucebrush.run_recipe(all_funcs, saucebrush.emitters.CSVEmitter(open('test.csv', 'w'), fields))

    for chamber in chambers:
        for year in years:
            for bill in get_bills_func(chamber, year):
                output.writerow(bill)
