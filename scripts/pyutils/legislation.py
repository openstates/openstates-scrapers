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

        # Associate each recorded vote with an actual legislator
        for vote in bill['votes']:
            for type in ['yes_votes', 'no_votes', 'other_votes']:
                vote[type] = map(lambda l:
                                 {'name': l,
                                  'leg_id': self.matcher[vote['chamber']][l]},
                                 vote[type])

        for sponsor in bill['sponsors']:
            if 'chamber' in sponsor:
                leg_id = self.matcher[sponsor['chamber']][sponsor['name']]
            else:
                leg_id = self.matcher[bill['chamber']][sponsor['name']]

            sponsor['leg_id'] = leg_id

        filename = "%s:%s:%s.json" % (bill['session'], bill['chamber'],
                                      bill['bill_id'])
        with open(os.path.join(self.output_dir, "bills", filename), 'w') as f:
            json.dump(bill, f)

    def add_legislator(self, legislator):
        self.log("add_legislator %s %s: %s" % (legislator['chamber'],
                                               legislator['session'],
                                               legislator['full_name']))

        self.matcher[legislator['chamber']][legislator] = [
            legislator['session'],
            legislator['chamber'],
            legislator['district']]

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
        for year in years:
            self.matcher = {'upper': NameMatcher(), 'lower': NameMatcher()}
            for chamber in chambers:
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
        self['type'] = 'bill'
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
        self['yes_votes'] = []
        self['no_votes'] = []
        self['other_votes'] = []
        self.update(kwargs)

    def yes(self, legislator):
        self['yes_votes'].append(legislator)

    def no(self, legislator):
        self['no_votes'].append(legislator)

    def other(self, legislator):
        self['other_votes'].append(legislator)


class Legislator(dict):

    def __init__(self, session, chamber, district, full_name,
                 first_name, last_name, middle_name, **kwargs):
        self['type'] = 'legislator'
        self['session'] = session
        self['chamber'] = chamber
        self['district'] = district
        self['full_name'] = full_name
        self['first_name'] = first_name
        self['last_name'] = last_name
        self['middle_name'] = middle_name
        self.update(kwargs)


class NameMatcher(object):
    """
    Match various forms of a name, provided they uniquely identify
    a person from everyone else we've seen.

    Given the name object:
     {'fullname': 'Michael J. Stephens', 'first_name': 'Michael',
      'last_name': 'Stephens', 'middle_name': 'Joseph'}
    we will match these forms:
     Michael J. Stephens
     Michael Stephens
     Stephens
     Stephens, Michael
     Stephens, M
     Stephens, Michael Joseph
     Stephens, Michael J
     Stephens, M J
     M Stephens
     M J Stephens
     Michael Joseph Stephens

    Tests:

    >>> nm = NameMatcher()
    >>> nm[{'fullname': 'Michael J. Stephens', 'first_name': 'Michael', \
            'last_name': 'Stephens', 'middle_name': 'J'}] = 1
    >>> assert nm['Michael J. Stephens'] == 1
    >>> assert nm['Stephens'] == 1
    >>> assert nm['Michael Stephens'] == 1
    >>> assert nm['Stephens, M'] == 1
    >>> assert nm['Stephens, Michael'] == 1
    >>> assert nm['Stephens, M J'] == 1

    Add a similar name:

    >>> nm[{'fullname': 'Mike J. Stephens', 'first_name': 'Mike', \
            'last_name': 'Stephens', 'middle_name': 'Joseph'}] = 2

    Unique:

    >>> assert nm['Mike J. Stephens'] == 2
    >>> assert nm['Mike Stephens'] == 2
    >>> assert nm['Michael Stephens'] == 1

    Not unique anymore:

    >>> assert nm['Stephens'] == None
    >>> assert nm['Stephens, M'] == None
    >>> assert nm['Stephens, M J'] == None
    """

    def __init__(self):
        self.names = {}

    def __setitem__(self, name, obj):
        """
        Expects a dictionary with fullname, first_name, last_name and
        middle_name elements as key.

        While this can grow quickly, we should never be dealing with
        more than a few hundred legislators at a time so don't worry about
        it.
        """

        def add(name):
            name = name.replace('.', '').lower()
            if name in self.names:
                # This form is not unique
                self.names[name] = None
            else:
                self.names[name] = obj

        #add(name['fullname'])
        if name['last_name']:
            add(name['last_name'])

        if name['last_name'] and name['first_name']:
            add("%s, %s" % (name['last_name'], name['first_name']))
            add("%s %s" % (name['first_name'], name['last_name']))

            if len(name['first_name']) > 1:
                add("%s %s" % (name['first_name'][0], name['last_name']))
                add("%s, %s" % (name['last_name'], name['first_name'][0]))

            if name['middle_name']:
                add("%s, %s %s" % (name['last_name'], name['first_name'],
                                   name['middle_name']))
                add("%s %s %s" % (name['first_name'], name['middle_name'],
                                  name['last_name']))

                if len(name['first_name']) > 1:
                    add("%s, %s %s" % (name['last_name'],
                                       name['first_name'][0],
                                       name['middle_name']))

                if len(name['middle_name']) > 1:
                    add("%s, %s %s" % (name['last_name'], name['first_name'],
                                  name['middle_name'][0]))
                    add("%s %s %s" % (name['first_name'],
                                      name['middle_name'][0],
                                      name['last_name']))

                if (len(name['middle_name']) > 1 and
                    len(name['first_name']) > 1):
                    add("%s, %s %s" % (name['last_name'],
                                       name['first_name'][0],
                                       name['middle_name'][0]))

    def __getitem__(self, name):
        name = name.strip().replace('.', '').lower()
        if name in self.names:
            return self.names[name]
        return None
