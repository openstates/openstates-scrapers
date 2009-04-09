from optparse import make_option, OptionParser
import datetime
import csv
import os.path

class ScrapeError(Exception):
    """
    Base class for scrape errors.
    """
    pass

class NoDataForYear(ScrapeError):
    """ exception to be raised when no data exists for a given year """

    def __init__(self, year):
        self.year = year

    def __str__(self):
        return 'No data exists for %s' % year

class UnsupportedFormat(ScrapeError):
    """
    The requested processing covers an unsupported file format.
    """

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
    raise DeprecationWarning('run_legislator_method is deprecated')

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

    # setup dictionary writer with blanks for missing values, and 
    # ignoring extra values in dictionary
    output = csv.DictWriter(open('output.csv', 'w'), fields, '', 'ignore')

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

class LegislationScraper(object):
    option_list = (
        make_option('-y', '--year', action='append', dest='years',
                    help='year(s) to scrape'),
        make_option('--all', action='store_true', dest='all_years',
                    default=False, help='scrape all data (overrides --year)'),
        make_option('--upper', action='store_true', dest='upper', default=False,
                    help='scrape upper chamber'),
        make_option('--lower', action='store_true', dest='lower', default=False,
                    help='scrape lower chamber'),
        make_option('-v', '--verbose', action='store_true', dest='verbose',
                    default=False, help="be verbose")
        make_option('-d', '--output_dir', action='store', dest='output_dir',
                    help='output directory'),
    )

    common_fields = ['bill_state', 'bill_chamber', 'bill_session', 'bill_id']
    bill_fields = common_fields + ['bill_name']
    bill_version_fields = common_fields + ['version_name', 'version_url']
    sponsor_fields = common_fields + ['sponsor_type', 'sponsor_name']
    action_fields = common_fields + ['action_chamber', 'action_text', 'action_date']
    output_dir = None

    def __init__(self):
        if not hasattr(self, 'state'):
            raise Exception('LegislationScrapers must have a state attribute')
    
    def add_bill(self, bill_chamber, bill_session, bill_id, bill_name, **kwargs):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'bill_name': bill_name}
        row.update(kwargs)
        self.be_verbose("add_bill %s %s: %s" % (row['bill_chamber'],
                                                row['bill_session'],
                                                row['bill_id']))
        self.bill_csv.writerow(row)

    def add_bill_version(self, bill_chamber, bill_session, bill_id, version_name, version_url, **kwargs):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'version_name': version_name, 'version_url': version_url}
        row.update(kwargs)
        self.be_verbose("add_bill_version %s %s: %s.%s" % (row['bill_chamber'],
                                                           row['bill_session'],
                                                           row['bill_id'],
                                                           row['version_name']))
        self.version_csv.writerow(row)

    def add_sponsorship(self, bill_chamber, bill_session, bill_id, sponsor_type, sponsor_name, **kwargs):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'sponsor_type': sponsor_type, 'sponsor_name': sponsor_name}
        row.update(kwargs)
        self.be_verbose("add_sponsorship %s %s: %s sponsors (%s) %s" %
                        (row['bill_chamber'],
                         row['bill_session'],
                         row['bill_id'],
                         row['sponsor_type'],
                         row['sponsor_name']))
        self.sponsor_csv.writerow(row)

    def add_action(self, bill_chamber, bill_session, bill_id, action_chamber, action_text, action_date, **kwargs):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'action_chamber': action_chamber, 'action_text': action_text,
               'action_date': action_date}
        row.update(kwargs)
        self.be_verbose("add_action %s %s: %s action '%s...' in %s" %
                        (row['bill_chamber'],
                         row['bill_session'],
                         row['bill_id'],
                         row['action_text'][:50],
                         row['action_chamber']))
        self.action_csv.writerow(row)

    def be_verbose(self, msg):
        if self.verbose:
            if isinstance(msg, unicode):
                msg = msg.encode('utf-8')
            print "%s: %s" % (self.state, msg)

    def scrape_bills(self, chamber, year):
        raise NotImplementedError('LegislatorScrapers must define a scrape_bills method')

    def init_output_files(self,output_dir):

        if output_dir == None:
            output_dir = os.path.join(os.path.curdir,"data",self.state)


        try:
            os.makedirs(output_dir)
        except OSError,e:
            if e.errno != 17 or os.path.isfile(output_dir): # 17 == File exists
                raise e

        bill_filename = os.path.join(output_dir,'legislation.csv')
        self.bill_csv = csv.DictWriter(open(bill_filename, 'w'), 
                                       self.bill_fields, extrasaction='ignore')

        bill_version_filename = os.path.join(output_dir,'bill_versions.csv')
        self.version_csv = csv.DictWriter(open(bill_version_filename, 'w'),
                                          self.bill_version_fields,
                                          extrasaction='ignore')

        sponsor_filename = os.path.join(output_dir,'sponsorships.csv')
        self.sponsor_csv = csv.DictWriter(open(sponsor_filename, 'w'),
                                          self.sponsor_fields, 
                                          extrasaction='ignore')

        action_filename = os.path.join(output_dir,'actions.csv')
        self.action_csv = csv.DictWriter(open(action_filename, 'w'),
                                         self.action_fields,
                                         extrasaction='ignore')
    

    def run(self):
        options, spares = OptionParser(option_list=self.option_list).parse_args()

        self.verbose = options.verbose

        if options.output_dir:
            self.output_dir = options.output_dir
            
        self.init_output_files(self.output_dir)

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
        for chamber in chambers:
            for year in years:
                try:
                    self.scrape_bills(chamber, year)
                except NoDataForYear, e:
                    if options.all_years:
                        pass
                    else:
                        raise

