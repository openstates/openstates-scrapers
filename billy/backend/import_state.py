#!/usr/bin/env python
import logging
import argparse

from fiftystates import settings

from fiftystates.backend.metadata import import_metadata
from fiftystates.backend.bills import import_bills
from fiftystates.backend.legislators import import_legislators
from fiftystates.backend.committees import import_committees
from fiftystates.backend.votes import import_votes
from fiftystates.backend.events import import_events
from fiftystates.backend.versions import import_versions

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        add_help=False,
        description=('Import scraped state data into database.'))

    parser.add_argument('state', type=str,
                        help=('the two-letter abbreviation of the '
                              'state to import'))
    parser.add_argument('-v', '--verbose', action='count',
                        dest='verbose', default=False,
                        help=("be verbose (use multiple times for "
                              "more debugging information)"))
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

    # configure logger
    if args.verbose == 0:
        verbosity = logging.WARNING
    elif args.verbose == 1:
        verbosity = logging.INFO
    else:
        verbosity = logging.DEBUG

    logging.basicConfig(level=verbosity,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")

    # if any importers are specified, don't do all
    scrape_all = not any((args.bills, args.legislators, args.committees,
                          args.votes, args.events, args.versions))

    # always import metadata
    import_metadata(args.state, data_dir)

    if args.legislators or scrape_all:
        import_legislators(args.state, data_dir)
    if args.bills or scrape_all:
        import_bills(args.state, data_dir)
    if args.committees or scrape_all:
        import_committees(args.state, data_dir)
    if args.votes or scrape_all:
        import_votes(args.state, data_dir)

    # events and versions currently excluded from scrape_all
    if args.events:
        import_events(args.state, data_dir)
    if args.versions:
        import_versions(args.state, args.rpm)
