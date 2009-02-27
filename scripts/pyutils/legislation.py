from optparse import make_option, OptionParser
import csv

class LegislationScraper(object):

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

    def __init__(self, filename):
        options, spares = OptionParser(option_list=self.option_list).parse_args()
        self.years = options.years
        self.chambers = []
        if options.upper:
            self.chambers.append('upper')
        if options.lower:
            self.chambers.append('lower')
        self.download = options.download
        self.filename = filename
        self.fields = ('state', 'chamber', 'session', 'bill_id', 'remote_url', 'local_filename')
        self.outfile = csv.DictWriter(open(filename, 'w'), self.fields)

    def scrape_legislation(self, chamber, year, download):
        raise NotImplementedError('scrape_legislation should be defined in a subclass of LegislationScraper')

    def add_bill(self, state, chamber, session, bill_id, remote_url, local_filename=''):
        # this will keep track of what has been seen before, etc.
        self.outfile.writerow({'state': state, 'chamber':chamber,
                               'session':session, 'bill_id': bill_id,
                               'remote_url': remote_url,
                               'local_filename': local_filename})

    def run(self):
        for year in self.years:
            for chamber in self.chambers:
                self.scrape_legislation(chamber, year, self.download)

