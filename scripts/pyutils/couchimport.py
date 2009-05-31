#!/usr/bin/env python
import unicodecsv as csv
from couchdb.client import Server
import argparse
import sys
import re


class NameMatcher(object):
    """
    Match various forms of a name, provided they uniquely identify
    a person from everyone else we've seen.

    Given the name object:
     {'fullname': 'Michael J. Stephens', 'first_name': 'Michael',
      'last_name': 'Stephens', 'middle_name': 'J'}
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


class CouchImporter(object):

    def __init__(self, state, verbose=False):
        self.state = state
        self.verbose = verbose
        self.cache = {}
        self.legislators = {}
        self.server = Server('http://localhost:5984')
        self.db = self.server[state]
        self.log('Database loaded.')

    def log(self, msg):
        if self.verbose:
            print "%s: %s" % (self.state, msg)

    def get(self, id):
        if id in self.cache:
            return self.cache[id]
        else:
            self.cache[id] = self.db.get(id, default={'_id': id})
            return self.cache[id]

    def put(self, id, doc):
        doc['_id'] = id
        self.cache[id] = doc

    def update(self):
        self.db.update(self.cache.values())
        self.cache = {}

    def import_all(self):
        self.log("Importing data")
        self.import_legislators(False)
        self.import_bills(False)
        self.import_actions(False)
        self.import_sponsors(False)
        self.import_versions(False)
        self.import_votes(False)
        self.update()

    def import_bills(self, flush_cache=True):
        filename = 'data/%s/legislation.csv' % self.state
        reader = csv.DictReader(open(filename, 'r'),
                                ['state', 'chamber', 'session', 'bill_id',
                                 'title'])

        for row in reader:
            doc = self.get(self.bill_id(row))
            doc.update(row)
            doc['type'] = 'bill'

        if flush_cache:
            self.update()

    def import_actions(self, flush_cache=True):
        filename = 'data/%s/actions.csv' % self.state
        reader = csv.DictReader(open(filename, 'r'),
                                ['state', 'chamber', 'session', 'bill_id',
                                 'actor', 'action_text', 'action_date'])

        for row in reader:
            id = self.bill_id(row)
            bill = self.get(id)
            action = {'actor': row['actor'], 'text': row['action_text'],
                      'date': row['action_date']}

            if 'actions' in bill:
                if not action in bill['actions']:
                    bill['actions'].append(action)
            else:
                bill['actions'] = [action]

        if flush_cache:
            self.update()

    def import_sponsors(self, flush_cache=True):
        filename = 'data/%s/sponsorships.csv' % self.state
        reader = csv.DictReader(open(filename, 'r'),
                                ['state', 'chamber', 'session', 'bill_id',
                                 'sponsor_type', 'sponsor_name'])

        for row in reader:
            id = self.bill_id(row)
            bill = self.get(id)
            sponsor = {'type': row['sponsor_type'],
                       'name': row['sponsor_name']}

            match = self.lookup_legislator(row['session'],
                                           row['chamber'],
                                           row['sponsor_name'])
            if not match:
                self.log("Couldn't find matching legislator for:")
                self.log(row)

            sponsor['leg_id'] = match

            if 'sponsors' in bill:
                if not sponsor in bill['sponsors']:
                    bill['sponsors'].append(sponsor)
            else:
                bill['sponsors'] = [sponsor]

        if flush_cache:
            self.update()

    def import_versions(self, flush_cache=True):
        filename = 'data/%s/bill_versions.csv' % self.state
        reader = csv.DictReader(open(filename, 'r'),
                                ['state', 'chamber', 'session', 'bill_id',
                                 'version_name', 'version_url'])

        for row in reader:
            id = self.bill_id(row)
            bill = self.get(id)
            version = {'name': row['version_name'],
                       'url': row['version_url']}

            if 'versions' in bill:
                if not version in bill['versions']:
                    bill['versions'].append(version)
            else:
                bill['versions'] = [version]

        if flush_cache:
            self.update()

    def import_votes(self, flush_cache=True):
        filename = 'data/%s/votes.csv' % self.state
        reader = csv.DictReader(open(filename, 'r'),
                                ['state', 'chamber', 'session', 'bill_id',
                                 'date', 'vote_chamber', 'vote_location',
                                 'motion', 'passed',
                                 'threshold', 'yes_count', 'no_count',
                                 'other_count', 'yes_votes', 'no_votes',
                                 'other_votes'])

        for row in reader:

            def lookup_id(name):
                return {'name': name,
                        'leg_id': self.lookup_legislator(row['session'],
                                                         row['vote_chamber'],
                                                         name)}

            id = self.bill_id(row)
            bill = self.get(id)

            vote = {'date': row['date'], 'chamber': row['vote_chamber'],
                    'location': row['vote_location'],
                    'motion': row['motion'], 'threshold': row['threshold'],
                    'yes_count': row['yes_count'], 'no_count': row['no_count'],
                    'other_count': row['other_count']}

            if row['passed'] == "True":
                vote['passed'] = True
            else:
                vote['passed'] = False

            if row['yes_votes'] or row['no_votes'] or row['other_votes']:
                for vtype in ['yes_votes', 'no_votes', 'other_votes']:
                    votes = row[vtype].split('|')
                    vote[vtype] = filter(None, votes)
                    vote[vtype] = map(lookup_id, vote[vtype])

            if 'votes' in bill:
                if not vote in bill['votes']:
                    bill['votes'].append(vote)
            else:
                bill['votes'] = [vote]

        if flush_cache:
            self.update()

    def legislator_exists(self, chamber, district, session):
        """
        Check if the legislator has already been imported. Can handle
        both individual and merged records.
        """
        matches = self.db.view('app/leg-with-sessions')[[chamber,
                                                         district,
                                                         session]]
        return len(matches) > 0

    def import_legislators(self, flush_cache=True):
        filename = 'data/%s/legislators.csv' % self.state
        reader = csv.DictReader(open(filename, 'r'),
                                ['state', 'chamber', 'session', 'district',
                                 'fullname', 'first_name', 'last_name',
                                 'middle_name', 'suffix', 'party'])

        for row in reader:
            session_num = int(row['session'])

            if self.legislator_exists(row['chamber'], row['district'],
                                      session_num):
                # Don't need to add to db
                self.saw_legislator(row, self.legislator_id(row))
            else:
                # Look for people with this exact name and matching
                # chamber/district already in the database
                for match in self.db.view('app/leg-duplicates',
                                          include_docs=True)[
                    [row['chamber'],
                     row['district'],
                     row['fullname']]]:
                    # Check if this match coincides with an adjacent session
                    # (we assume that consecutive sessions are represented
                    # by consecutive integers - need a strategy for states
                    # where this is not true)
                    if (session_num + 1 in match.doc['sessions'] or
                        session_num - 1 in match.doc['sessions']):
                        # Add on to existing legislator
                        match.doc['sessions'].append(session_num)

                        # Write directly to the DB instead of caching
                        # so that our view will be updated next read
                        # (same thing below)
                        self.db.update([match.doc])

                        self.saw_legislator(row, match.doc['_id'])

                        break  # will skip the else block
                else:
                    # We didn't find a match, so create a new legislator doc
                    leg_id = self.legislator_id(row)
                    self.saw_legislator(row, leg_id)
                    row['type'] = 'legislator'
                    row['sessions'] = [session_num]
                    del row['session']
                    self.db[leg_id] = row

        if flush_cache:
            self.update()

    def saw_legislator(self, row, leg_id):
        session = row['session']
        chamber = row['chamber']
        if not session in self.legislators:
            self.legislators[session] = {}
        if not chamber in self.legislators[session]:
            self.legislators[session][chamber] = NameMatcher()
        self.legislators[session][chamber][row] = leg_id

    def lookup_legislator(self, session, chamber, name):
        # TODO: get rid of this state-specific code
        if self.state == 'ca':
            session = session[0:8]
        elif self.state == 'ut':
            session = re.match('(\d+)', session).group(1)

        if (session in self.legislators and
            chamber in self.legislators[session]):
            return self.legislators[session][chamber][name]
        else:
            return None

    def bill_id(self, row):
        return 'bill:%s:%s:%s' % (row['session'],
                                  row['chamber'],
                                  row['bill_id'])

    def legislator_id(self, row):
        return 'legislator:%s:%s:%s' % (row['chamber'],
                                        row['district'],
                                        row['session'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import state legislative data into a CouchDB instance.")
    parser.add_argument('states', metavar='state', nargs='+',
                        help='the state(s) to import')
    parser.add_argument('-v', '--verbose', action='store_true')
    # TODO: couch host option, maybe option for non-default DB name

    args = parser.parse_args()

    for state in args.states:
        ci = CouchImporter(state, verbose=args.verbose)
        ci.import_all()
