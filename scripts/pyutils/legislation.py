from optparse import make_option, OptionParser
import datetime
import csv
import os
import urllib2
from hashlib import md5
try:
    import json
except ImportError:
    import simplejson as json


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


class LegislationScraper(object):
    option_list = (
        make_option('-y', '--year', action='append', dest='years',
                    help='year(s) to scrape'),
        make_option('--all', action='store_true', dest='all_years',
                    default=False, help='scrape all data (overrides --year)'),
        make_option('--upper', action='store_true', dest='upper',
                    default=False, help='scrape upper chamber'),
        make_option('--lower', action='store_true', dest='lower',
                    default=False, help='scrape lower chamber'),
        make_option('-v', '--verbose', action='store_true', dest='verbose',
                    default=False, help="be verbose"),
        make_option('-d', '--output_dir', action='store', dest='output_dir',
                    help='output directory'),
    )
    cache_dir = 'cache'
    output_dir = None

    def __init__(self):
        if not hasattr(self, 'state'):
            raise Exception('LegislationScrapers must have a state attribute')

    def urlopen(self, url):
        """
        Grabs a URL, returning a cached version if available.
        """
        url_cache = os.path.join(self.cache_dir, self.state,
                                 md5(url).hexdigest()+'.html')
        if os.path.exists(url_cache):
            return open(url_cache).read()
        data = urllib2.urlopen(url).read()
        open(url_cache, 'w').write(data)
        return data

    def log(self, msg):
        """
        Output debugging information if verbose mode is enabled.
        """
        if self.verbose:
            if isinstance(msg, unicode):
                msg = msg.encode('utf-8')
            print "%s: %s" % (self.state, msg)

    def init_dirs(self):

        def makedir(path):
            try:
                os.makedirs(path)
            except OSError, e:
                if e.errno != 17 or os.path.isfile(self.output_dir):
                    raise e

        makedir(os.path.join(self.output_dir, "bills"))
        makedir(os.path.join(self.output_dir, "legislators"))
        makedir(os.path.join(self.cache_dir, self.state))

    def add_bill(self, bill):
        self.log("add_bill %s %s: %s" % (bill['chamber'],
                                         bill['session'],
                                         bill['bill_id']))

        filename = "%s:%s:%s.json" % (bill['session'], bill['chamber'],
                                      bill['bill_id'])
        with open(os.path.join(self.output_dir, "bills", filename), 'w') as f:
            json.dump(bill, f)

    def add_legislator(self, legislator):
        self.log("add_legislator %s %s: %s" % (legislator['chamber'],
                                               legislator['session'],
                                               legislator['full_name']))

        filename = "%s:%s:%s.json" % (legislator['session'],
                                      legislator['chamber'],
                                      legislator['district'])
        with open(os.path.join(self.output_dir, "legislators", filename),
                  'w') as f:
            json.dump(legislator, f)

    def write_metadata(self):
        with open(os.path.join(self.output_dir, 'state_metadata.json'),
                  'w') as f:
            json.dump(self.metadata, f)

    def run(self):
        options, spares = OptionParser(
            option_list=self.option_list).parse_args()

        self.verbose = options.verbose

        if options.output_dir:
            self.output_dir = options.output_dir
        else:
            self.output_dir = os.path.join(os.path.curdir, "data",
                                           self.state)
        self.init_dirs()
        self.write_metadata()

        years = options.years
        if options.all_years:
            years = [str(y) for y in range(1969,
                                           datetime.datetime.now().year+1)]
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
                    self.scrape_legislators(chamber, year)
                    self.scrape_bills(chamber, year)
                except NoDataForYear, e:
                    if options.all_years:
                        pass
                    else:
                        raise


class Bill(dict):

    def __init__(self, session, chamber, bill_id, title, **kwargs):
        self['session'] = session
        self['chamber'] = chamber
        self['bill_id'] = bill_id
        self['title'] = title
        self['sponsors'] = []
        self['votes'] = []
        self['versions'] = []
        self['actions'] = []
        self.update(kwargs)

    def add_sponsor(self, type, name, **kwargs):
        self['sponsors'].append(dict(type=type, name=name, **kwargs))

    def add_version(self, name, url, **kwargs):
        self['versions'].append(dict(name=name, url=url, **kwargs))

    def add_action(self, actor, action, date, **kwargs):
        self['actions'].append(dict(actor=actor, action=action,
                                    date=str(date), **kwargs))

    def add_vote(self, vote):
        self['votes'].append(vote)


class Vote(dict):

    def __init__(self, chamber, location, date, motion, passed,
                 yes_count, no_count, other_count, **kwargs):
        self['chamber'] = chamber
        self['location'] = location
        self['date'] = str(date)
        self['motion'] = motion
        self['passed'] = passed
        self['yes_count'] = yes_count
        self['no_count'] = no_count
        self['other_count'] = other_count
        self['yes'] = []
        self['no'] = []
        self['other'] = []
        self.update(kwargs)

    def yes(self, legislator):
        self['yes'].append(legislator)

    def no(self, legislator):
        self['no'].append(legislator)

    def other(self, legislator):
        self['other'].append(legislator)


class Legislator(dict):

    def __init__(self, session, chamber, district, full_name,
                 first_name, last_name, middle_name, **kwargs):
        self['session'] = session
        self['chamber'] = chamber
        self['district'] = district
        self['full_name'] = full_name
        self['first_name'] = first_name
        self['last_name'] = last_name
        self['middle_name'] = middle_name
        self.update(kwargs)
