#!/usr/bin/env python
from couchdb.client import Server
import argparse
import os
from schemas import StateMetadata, Legislator, Bill
try:
    import json
except ImportError:
    import simplejson as json


class Exporter(object):

    def __init__(self, state, output_dir, verbose=False):
        self.state = state
        self.verbose = verbose
        self.output_dir = os.path.join(output_dir, self.state)

    def log(self, msg):
        if self.verbose:
            print "%s: %s" % (self.state, msg)

    def run(self):
        server = Server()
        assert self.state in server
        db = server[self.state]

        # Grab metadata first so exporter can set up directory structure, etc.
        # based on it
        self.saw_metadata(StateMetadata.get(db))

        for bill in Bill.all(db):
            self.saw_bill(bill)

        for legislator in Legislator.all(db):
            self.saw_legislator(legislator)

    def saw_metadata(self, doc):
        raise NotImplementedError('Override saw_metadata')

    def saw_bill(self, doc):
        raise NotImplementedError('Override saw_bill')

    def saw_legislator(self, doc):
        raise NotImplementedError('Override saw_legislator')


class JSONExporter(Exporter):

    def saw_metadata(self, metadata):

        def makedir(dir):
            try:
                os.makedirs(os.path.join(self.output_dir, dir))
            except OSError, e:
                if e.errno != 17:
                    raise e

        self.log('creating directory structure')
        makedir('bills')
        makedir('legislators')

        for (session, details) in metadata.session_details.items():
            makedir(os.path.join('bills', session))

            for sub_session in details['sub_sessions']:
                makedir(os.path.join('bills', sub_session))

        self.log('writing metadata')
        with open(os.path.join(self.output_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata._data, f)

    def saw_bill(self, bill):
        self.log('writing bill %s' % bill.id)
        with open(os.path.join(self.output_dir, 'bills', bill.session,
                               bill.bill_id + '.json'), 'w') as f:
            json.dump(bill._data, f)

    def saw_legislator(self, legislator):
        self.log('writing legislator %s' % legislator.id)
        filename = '.'.join(legislator.id.split(':')[1:]) + '.json'
        with open(os.path.join(self.output_dir, 'legislators',
                               filename), 'w') as f:
            json.dump(legislator._data, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export state legislative data from a CouchDB instance.")
    parser.add_argument('states', metavar='state', nargs='+',
                        help='the state(s) to import')
    parser.add_argument('--json', '-j', action='store_true',
                        help="export JSON data")
    parser.add_argument('--output', '-o', default='./export',
                        help="the directory to output data to")
    parser.add_argument('-v', '--verbose', action='store_true')
    # TODO: couch host option, maybe option for non-default DB name

    args = parser.parse_args()

    for state in args.states:
        if args.json:
            je = JSONExporter(state, args.output,
                              verbose=args.verbose)
            je.run()
