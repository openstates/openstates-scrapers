#!/usr/bin/env python
from couchdb.client import Server
import argparse
import os
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
        self.saw_metadata(db['state_metadata'])

        results = db.view('_all_docs', limit=200, include_docs=True)

        while len(results) > 0:
            for row in results:
                if 'type' in row.doc:
                    if row.doc['type'] == 'bill':
                        self.saw_bill(row.doc)
                    elif row.doc['type'] == 'legislator':
                        self.saw_legislator(row.doc)
            results = db.view('_all_docs', limit=200, include_docs=True,
                              startkey_docid=row.doc['_id'],
                              skip=1)

    def saw_metadata(self, doc):
        raise NotImplementedError('Override saw_metadata')

    def saw_bill(self, doc):
        raise NotImplementedError('Override saw_bill')

    def saw_legislator(self, doc):
        raise NotImplementedError('Override saw_legislator')


class JSONExporter(Exporter):

    def saw_metadata(self, doc):

        def makedir(dir):
            try:
                os.makedirs(os.path.join(self.output_dir, dir))
            except OSError, e:
                if e.errno != 17:
                    raise e

        self.log('creating directory structure')
        makedir('bills')
        makedir('legislators')

        for (session, details) in doc['session_details'].items():
            makedir(os.path.join('bills', session))

            for sub_session in details['sub_sessions']:
                makedir(os.path.join('bills', sub_session))

        self.log('writing metadata')
        with open(os.path.join(self.output_dir, 'metadata.json'), 'w') as f:
            json.dump(doc, f)

    def saw_bill(self, doc):
        self.log('writing bill %s' % doc['_id'])
        with open(os.path.join(self.output_dir, 'bills', doc['session'],
                               doc['bill_id'] + '.json'), 'w') as f:
            json.dump(doc, f)

    def saw_legislator(self, doc):
        self.log('writing legislator')
        filename = '.'.join(doc['_id'].split(':')[1:]) + '.json'
        with open(os.path.join(self.output_dir, 'legislators',
                               filename), 'w') as f:
            json.dump(doc, f)

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
