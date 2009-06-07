#!/usr/bin/env python
from couchdb.client import Server
import argparse
import sys
import os
import re
import glob
from schemas import StateMetadata, Legislator, Bill
sys.path.append('../scripts/pyutils')
import unicodecsv as csv
try:
    import json
except ImportError:
    import simplejson as json


class CouchImporter(object):

    def __init__(self, state, data_dir='../data', verbose=False):
        self.state = state
        self.data_dir = os.path.join(data_dir, state)
        self.verbose = verbose
        self.cache = {}

        self.server = Server()
        assert state in self.server
        self.db = self.server[state]

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
        self.import_metadata()
        self.import_legislators()
        self.import_bills()

    def import_metadata(self):
        filename = os.path.join(self.data_dir, 'state_metadata.json')

        with open(filename) as f:
            metadata = json.load(f)

        if 'state_metadata' in self.db:
            del self.db['state_metadata']
        self.db['state_metadata'] = metadata

        self.metadata = StateMetadata.get(self.db)

    def import_legislators(self):
        filenames = glob.glob(os.path.join(self.data_dir, 'legislators', '*'))

        for filename in filenames:
            with open(filename) as f:
                legislator = json.load(f)

            if Legislator.for_district_and_session(self.db,
                                                   legislator['chamber'],
                                                   legislator['district'],
                                                   legislator['session']):
                continue

            # Look for merge candidates
            for match in Legislator.duplicates(self.db, legislator['chamber'],
                                               legislator['district'],
                                               legislator['full_name']):
                if self.is_adjacent(legislator['session'], match.sessions):
                    # Add on to existing legislator
                    match.sessions.append(legislator['session'])
                    match.store(self.db)
                    break
            else:
                # No match. add to db
                doc_id = 'legislator:%s:%s:%s' % (legislator['chamber'],
                                                  legislator['district'],
                                                  legislator['session'])
                legislator['sessions'] = [legislator['session']]
                del legislator['session']
                self.get(doc_id).update(legislator)
                self.update()

        self.update()

    def import_bills(self):
        filenames = glob.glob(os.path.join(self.data_dir, 'bills', '*'))

        for filename in filenames:
            with open(filename) as f:
                bill = json.load(f)
            doc_id = 'bill:%s:%s:%s' % (bill['session'], bill['chamber'],
                                        bill['bill_id'])
            self.get(doc_id).update(bill)

        self.update()

    def is_adjacent(self, session, sessions):
        """
        Returns true if session is adjacent to any element of sessions.
        """
        for s in sessions:
            if self.metadata.sessions_adjacent(session, s):
                return True
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import state legislative data into a CouchDB instance.")
    parser.add_argument('states', metavar='state', nargs='+',
                        help='the state(s) to import')
    parser.add_argument('-d', '--dir', default="../data",
                         help="the root directory of your data files")
    parser.add_argument('-v', '--verbose', action='store_true')
    # TODO: couch host option, maybe option for non-default DB name

    args = parser.parse_args()

    for state in args.states:
        ci = CouchImporter(state, data_dir=args.dir, verbose=args.verbose)
        ci.import_all()
