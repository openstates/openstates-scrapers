from optparse import make_option, OptionParser
import datetime
import csv
import os
import urllib2
from hashlib import md5

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
                    default=False, help="be verbose"),
        make_option('-d', '--output_dir', action='store', dest='output_dir',
                    help='output directory'),
    )

    cache_dir = 'cache'
    common_fields = ['bill_state', 'bill_chamber', 'bill_session', 'bill_id']
    bill_fields = common_fields + ['bill_name']
    bill_version_fields = common_fields + ['version_name', 'version_url']
    sponsor_fields = common_fields + ['sponsor_type', 'sponsor_name']
    action_fields = common_fields + ['actor', 'action_text', 'action_date']
    vote_fields = common_fields + ['vote_date', 'vote_chamber', 'vote_location',
                                   'vote_motion', 'vote_passed',
                                   'vote_threshold',
                                   'yes_count', 'no_count', 'other_count',
                                   'yes_votes', 'no_votes', 'other_votes']
    legislator_fields = ['legislator_state', 'legislator_chamber',
                         'legislator_session', 'legislator_district',
                         'legislator_fullname', 'legislator_first_name',
                         'legislator_last_name', 'legislator_middle_name',
                         'legislator_suffix', 'legislator_party']
    output_dir = None

    def __init__(self):
        if not hasattr(self, 'state'):
            raise Exception('LegislationScrapers must have a state attribute')
    
    def urlopen(self, url):
        """
        Grabs a URL, returning a cached version if available.
        """
        url_cache = os.path.join(self.cache_dir, md5(url).hexdigest()+'.html')
        if os.path.exists(url_cache):
            return open(url_cache).read()
        data = urllib2.urlopen(url).read()
        open(url_cache, 'w').write(data)
        return data

    def add_bill(self, bill_chamber, bill_session, bill_id, bill_name, **kwargs):
        """
        Adds a parsed bill.

        :param bill_chamber: the chamber where the bill originated, "upper" or "lower"
        :param bill_session: the session the bill came from, in whatever format the state uses to identify sessions (e.g. 2007, 19, 2007B, 17 Special Session 2)
        :param bill_id: how the state identifies the bill (e.g. HB12, S. 2, S.B. 5)
        :param bill_name: a title or short summary given to the bill by the state
        """
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'bill_name': bill_name}
        row.update(kwargs)
        self.be_verbose("add_bill %s %s: %s" % (row['bill_chamber'],
                                                row['bill_session'],
                                                row['bill_id']))
        self.bill_csv.writerow(row)

    def add_bill_version(self, bill_chamber, bill_session, bill_id, version_name, version_url, **kwargs):
        """
        Adds a version of a bill's text.

        :param version_name: the name given to this version of the bill by the state (if they don't provide a name, try the date published or some other identifying information)
        :param version_url: the absolute URL to the text this version
        """
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
        """
        Associates a sponsor with a specific bill.

        :param sponsor_type: the type of sponsorship (e.g. 'primary', 'cosponsosor')
        :param sponsor_name: the name of the sponsor
        """
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

    def add_action(self, bill_chamber, bill_session, bill_id, actor, action_text, action_date, **kwargs):
        """
        Associates an action with a specific bill.

        :param actor: the chamber, person or office responsible for this action
        :param action_text: the text of the action as presented by the state (e.g. 'VOTE ON PASSAGE 20 Aye 13 Nay 2 Abs', 'Referred to Committee on Aging')
        :param action_date: the date that the action was performed
        """
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'actor': actor, 'action_text': action_text,
               'action_date': action_date}
        row.update(kwargs)
        self.be_verbose("add_action %s %s: %s action '%s...' by %s" %
                        (row['bill_chamber'],
                         row['bill_session'],
                         row['bill_id'],
                         row['action_text'][:50],
                         row['actor']))
        self.action_csv.writerow(row)

    def add_vote(self, bill_chamber, bill_session, bill_id, vote_date,
                 vote_chamber, vote_location, vote_motion, vote_passed,
                 vote_yes_count, vote_no_count, vote_other_count,
                 yes_votes=[], no_votes=[], other_votes=[],
                 vote_threshold='1/2'):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session, 'bill_id': bill_id,
               'vote_date': vote_date, 'vote_chamber': vote_chamber,
               'vote_location': vote_location,
               'vote_motion': vote_motion, 'vote_passed': vote_passed,
               'yes_count': vote_yes_count, 'no_count': vote_no_count,
               'other_count': vote_other_count,
               'yes_votes': '|'.join(yes_votes),
               'no_votes': '|'.join(no_votes),
               'other_votes': '|'.join(other_votes),
               'vote_threshold': vote_threshold}

        if vote_passed:
            result = 'PASS'
        else:
            result = 'FAIL'

        self.be_verbose('add_vote %s %s: %s @ %s on %s, %s/%s/%s %s' %
                        (bill_chamber, bill_session, bill_id,
                         vote_location, vote_date, vote_yes_count,
                         vote_no_count, vote_other_count, result))

        self.vote_csv.writerow(row)

    def add_legislator(self, chamber, session, district, fullname,
                       first_name, last_name, middle_name, suffix, party):
        row = {'legislator_state': self.state, 'legislator_chamber': chamber,
               'legislator_session': session, 'legislator_district': district,
               'legislator_fullname': fullname,
               'legislator_first_name': first_name,
               'legislator_last_name': last_name,
               'legislator_middle_name': middle_name,
               'legislator_suffix': suffix, 'legislator_party': party}

        self.be_verbose('add_legislator %s %s: %s %s (District %s)' %
                        (chamber, session, party, fullname, district))

        self.legislator_csv.writerow(row)

    def be_verbose(self, msg):
        """
        Output debugging information if verbose mode is enabled.
        """
        if self.verbose:
            if isinstance(msg, unicode):
                msg = msg.encode('utf-8')
            print "%s: %s" % (self.state, msg)

    def scrape_bills(self, chamber, year):
        """
        Scrape all the bills for a given chamber and year. Should raise a
        NoDataForYear exception if there is no data available for the
        given year.
        """
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

        vote_filename = os.path.join(output_dir, 'votes.csv')
        self.vote_csv = csv.DictWriter(open(vote_filename, 'w'),
                                        self.vote_fields,
                                        extrasaction='ignore')

        legislator_filename = os.path.join(output_dir, 'legislators.csv')
        self.legislator_csv = csv.DictWriter(open(legislator_filename, 'w'),
                                             self.legislator_fields,
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

