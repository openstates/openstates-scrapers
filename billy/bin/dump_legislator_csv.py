#!/usr/bin/env python
import csv
import argparse

from billy import db
from billy.utils import extract_fields
from billy.conf import settings, base_arg_parser


def check_state(state):
    legislators = db.legislators.find({
        'state': state,
        'active': True,
    })

    fields = ('_id', 'full_name', 'first_name', 'middle_name', 'last_name',
              'suffixes', 'nickname', 'state', 'chamber', 'district', 'party',
              'active', 'votesmart_id', 'transparencydata_id', 'photo_url')

    uniques = {'votesmart_id':set(), 'transparencydata_id': set()}

    writer = csv.DictWriter(open(state+'_legislators.csv', 'w'), fields)

    writer.writerow(dict(zip(fields, fields)))

    for leg in legislators:

        writer.writerow(extract_fields(leg, fields))

        # check other uniques
        for field in uniques.iterkeys():
            if leg.get(field, None):
                if leg[field] in uniques[field]:
                    print 'duplicate for %s=%s' % (field, leg[field])
                uniques[field].add(leg[field])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='get a CSV of legislator data',
        parents=[base_arg_parser],
    )

    parser.add_argument('states', metavar='STATE', type=str, nargs='+',
                        help='states to dump')

    args = parser.parse_args()

    settings.update(args)

    for state in args.states:
        check_state(state)
