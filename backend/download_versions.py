#!/usr/bin/env python
from couchdb.client import Server
import argparse
import sys
import urllib2
import os


def download_versions(state, verbose=False):
    """
    Download all undownloaded bill versions for a given state.
    """

    def log(msg):
        if verbose:
            print "%s: %s" % (state, msg)

    server = Server("http://localhost:5984")
    assert state in server
    db = server[state]

    results = db.view("app/not-downloaded")

    # We only download one version per bill each time through
    # because otherwise we end up with update conflicts.
    while len(results) > 0:
        seen = set()
        for row in results:
            if row.key[1] in seen:
                continue
            seen.add(row.key[1])

            log("getting %s" % row.value)

            try:
                data = urllib2.urlopen(row.value).read()
            except urllib2.HTTPError:
                log("failed downloading %s, skipping" % row.value)

            path = row.value.replace('http://', '/').replace('ftp://', '/')
            db.put_attachment({'_id': row.key[0], '_rev': row.key[1]},
                              data, filename=path)
        # View will be regenerated
        results = db.view("app/not-downloaded")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import state legislative data into a CouchDB instance.")
    parser.add_argument('states', metavar='state', nargs='+',
                        help='the state(s) to import')
    parser.add_argument('-v', '--verbose', action='store_true')
    # TODO: couch host option, maybe option for non-default DB name

    args = parser.parse_args()

    for state in args.states:
        download_versions(state, args.verbose)
