#!/usr/bin/env python
import os
import json
import random

from billy import db
from billy.conf import settings, base_arg_parser

import scrapelib
import lxml.etree
from oyster.client import get_configured_client

def oysterize_versions(state, update_mins=20000):
    oclient = get_configured_client()
    new_bills = list(db.bills.find({'state': state,
                                    'versions.url': {'$exists': True},
                                    'versions._oyster_id': {'$exists': False}})
                    )
    print '%s bills with versions to _oysterize' % len(new_bills)
    for bill in new_bills:
        for version in bill['versions']:
            if 'url' in version and '_oyster_id' not in version:
                try:
                    _id = oclient.track_url(version['url'],
                                            update_mins=update_mins,
                                            name=version['name'],
                                            state=bill['state'],
                                            session=bill['session'],
                                            chamber=bill['chamber'],
                                            bill_id=bill['bill_id'],
                                            openstates_bill_id=bill['_id'])
                    version['_oyster_id'] = _id
                except Exception as e:
                    print e

        # save bill after updating all versions
        db.bills.save(bill, safe=True)


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='send bill versions to oyster',
                                     parents=[base_arg_parser])
    parser.add_argument('states', nargs='+', help='states to oysterize')
    args = parser.parse_args()
    settings.update(args)

    for state in args.states:
        print "Oysterizing %s bill versions" % state
        oysterize_versions(state)


if __name__ == '__main__':
    main()
