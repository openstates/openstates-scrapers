#!/usr/bin/env python
import argparse

from billy.conf import base_arg_parser, settings

from billy.importers.metadata import import_metadata
from billy.importers.bills import import_bills
from billy.importers.legislators import import_legislators
from billy.importers.committees import import_committees
from billy.importers.events import import_events
from billy.importers.versions import import_versions
from billy.utils import configure_logging

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Import scraped state data into database.',
        parents=[base_arg_parser],
    )

    parser.add_argument('state', type=str,
                        help=('the two-letter abbreviation of the '
                              'state to import'))
    parser.add_argument('-r', '--rpm', type=int, default=60,
                        help=('maximum number of documents to download '
                              'per minute'))
    parser.add_argument('--bills', action='store_true',
                        help='scrape bill data')
    parser.add_argument('--legislators', action='store_true',
                        help='scrape legislator data')
    parser.add_argument('--committees', action='store_true',
                        help='scrape (separate) committee data')
    parser.add_argument('--events', action='store_true',
                        help='scrape event data')
    parser.add_argument('--versions', action='store_true',
                        help='pull down copies of bill versions')
    parser.add_argument('--alldata', action='store_true', dest='alldata',
                        default=False, help="import all available data")

    args = parser.parse_args()

    if not (args.bills or args.legislators or args.committees or
            args.events or args.versions or args.alldata):
        raise Exception("Must specify at least one type: --bills, "
                           "--legislators, --committees, --events, "
                           "--versions,  --alldata")

    settings.update(args)

    data_dir = settings.BILLY_DATA_DIR

    # configure logger
    configure_logging(args.verbose, args.state)

    # always import metadata
    import_metadata(args.state, data_dir)

    if args.legislators or args.alldata:
        import_legislators(args.state, data_dir)
    if args.bills or args.alldata:
        import_bills(args.state, data_dir)
    if args.committees or args.alldata:
        import_committees(args.state, data_dir)

    # events and versions currently excluded from --alldata
    if args.events:
        import_events(args.state, data_dir)
    if args.versions:
        import_versions(args.state, args.rpm)
