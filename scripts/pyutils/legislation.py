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
    )
    common_fields = ('bill_state', 'bill_chamber', 'bill_session', 'bill_id')
    bill_fields = common_fields + ('bill_name', 'bill_url')
    sponsor_fields = common_fields + ('sponsor_type', 'sponsor_name')
    action_fields = common_fields + ('action_chamber', 'action_text', 'action_date')

    def __init__(self):
        if not hasattr(self, 'state'):
            raise Exception('LegislationScrapers must have a state attribute')

        bill_filename = 'data/%s/legislation.csv' % self.state
        self.bill_csv = csv.DictWriter(open(bill_filename, 'w'), 
                                       self.bill_fields, extrasaction='ignore')
        sponsor_filename = 'data/%s/sponsorships.csv' % self.state
        self.sponsor_csv = csv.DictWriter(open(sponsor_filename, 'w'),
                                          self.sponsor_fields, 
                                          extrasaction='ignore')
        action_filename = 'data/%s/actions.csv' % self.state
        self.action_csv = csv.DictWriter(open(action_filename, 'w'),
                                         self.action_fields,
                                         extrasaction='ignore')

    def add_bill(self, bill_chamber, bill_session, bill_id, bill_name, bill_url, **kwargs):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'bill_name': bill_name, 'bill_url': bill_url}
        row.update(kwargs)
        self.bill_csv.writerow(row)

    def add_sponsorship(self, bill_chamber, bill_session, bill_id, sponsor_type, sponsor_name, **kwargs):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'sponsor_type': sponsor_type, 'sponsor_name': sponsor_name}
        row.update(kwargs)
        self.sponsor_csv.writerow(row)

    def add_action(self, bill_chamber, bill_session, bill_id, action_chamber, action_text, action_date, **kwargs):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'action_chamber': action_chamber, 'action_text': action_text,
               'action_date': action_date}
        row.update(kwargs)
        self.action_csv.writerow(row)

    def scrape_bills(self, chamber, year):
        raise NotImplementedError('LegislatorScrapers must define a scrape_bills method')

    def run(self):
        options, spares = OptionParser(option_list=self.option_list).parse_args()
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

