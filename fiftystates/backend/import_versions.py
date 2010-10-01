#!/usr/bin/env python
import sys
import logging
import argparse

from pymongo.son import SON

import scrapelib

from fiftystates.backend import db, fs
from fiftystates.backend.utils import base_arg_parser, put_document


def import_versions(state, rpm=60):
    scraper = scrapelib.Scraper(requests_per_minute=rpm)

    for bill in db.bills.find({'state': state}):
        logging.info("Importing %s" % bill['bill_id'])

        bill_changed = False
        for version in bill['versions']:
            if 'document_id' in version or 'url' not in version:
                continue

            doc = scraper.urlopen(version['url'])

            metadata = {'bill': {'state': bill['state'],
                                 'chamber': bill['chamber'],
                                 'session': bill['session'],
                                 'bill_id': bill['bill_id'],
                                 'title': bill['title']},
                        'name': version['name'],
                        'url': version['url']}

            content_type = doc.response.headers['content-type']

            version['document_id'] = put_document(doc, content_type,
                                                  metadata)
            bill_changed = True

        if bill_changed:
            db.bills.save(bill)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        parents=[base_arg_parser],
        description="Download and store copies of bill versions.")
    parser.add_argument('-r', '--rpm', type=int, default=60,
                        help=('maximum number of documents to download '
                              'per minute'))
    args = parser.parse_args()

    verbosity = {0: logging.WARNING,
                 1: logging.INFO}.get(args.verbose, logging.DEBUG)

    logging.basicConfig(level=verbosity,
                        format=("%(asctime)s %(name)s %(levelname)s " +
                                args.state + " %(message)s"),
                        datefmt="%H:%M:%S")

    import_versions(args.state, args.rpm)
