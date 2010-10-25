#!/usr/bin/env python
import os
import sys
import glob
import json
import datetime

from fiftystates import settings
from fiftystates.backend import db
from fiftystates.backend.utils import base_arg_parser

import argparse

from fiftystates.backend.import_metadata import import_metadata
from fiftystates.backend.import_bills import import_bills
from fiftystates.backend.import_legislators import import_legislators
from fiftystates.backend.import_committees import import_committees
from fiftystates.backend.import_votes import import_votes
from fiftystates.backend.import_events import import_events
from fiftystates.backend.import_versions import import_versions


def main():
    parser = argparse.ArgumentParser(
        parents=[base_arg_parser],
        description=('Import scraped state data into database.'))

    parser.add_argument('--data_dir', '-d', type=str,
                        help='the base Fifty State data directory')
    parser.add_argument('-r', '--rpm', type=int, default=60,
                        help=('maximum number of documents to download '
                              'per minute'))
    parser.add_argument('--bills', action='store_true',
                        help='scrape bill data')
    parser.add_argument('--legislators', action='store_true',
                        help='scrape legislator data')
    parser.add_argument('--committees', action='store_true',
                        help='scrape (separate) committee data')
    parser.add_argument('--votes', action='store_true',
                        help='scrape (separate) vote data')
    parser.add_argument('--events', action='store_true',
                        help='scrape event data')
    parser.add_argument('--versions', action='store_true',
                        help='pull down copies of bill versions')

    args = parser.parse_args()

    if args.data_dir:
        data_dir = args.data_dir
    else:
        data_dir = settings.FIFTYSTATES_DATA_DIR

    # if no importers are specified, set them all to true
    if not any((args.bills, args.legislators, args.committees, args.votes,
               args.events, args.versions)):
        args.bills = args.legislators = args.committees = args.votes = \
                args.events = args.versions = True

    # always import metadata
    import_metadata(args.state, data_dir)

    if args.legislators:
        import_legislators(args.state, data_dir)
    if args.bills:
        import_bills(args.state, data_dir)
    if args.committees:
        import_committees(args.state, data_dir)
    if args.votes:
        import_votes(args.state, data_dir)
    if args.events:
        import_events(args.state, data_dir)
    if args.versions:
        import_versions(args.state, args.rpm)

if __name__ == '__main__':
    main()
