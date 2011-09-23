#!/usr/bin/env python

from billy import db
from billy.utils import metadata
from billy.conf import settings, base_arg_parser
from billy.importers.legislators import deactivate_legislators
import datetime
import argparse


def retire_legislator(leg_id, date):
    legislator = db.legislators.find_one({'leg_id': leg_id})
    level = legislator['level']
    abbr = legislator[level]

    term = metadata(abbr)['terms'][-1]['name']
    cur_role = legislator['roles'][0]
    if cur_role['type'] != 'member' or cur_role['term'] != term:
        raise ValueError('member missing role for %s' % term)

    date = datetime.datetime.strptime(date, '%Y-%m-%d')
    cur_role['end_date'] = date
    db.legislators.save(legislator, safe=True)
    print('deactivating legislator {0}'.format(leg_id))
    deactivate_legislators(term, abbr, level)


def main():
    parser = argparse.ArgumentParser(
        description='set a legislators term end_date',
        parents=[base_arg_parser],
    )

    parser.add_argument('leg_id', type=str,
                        help='id of legislator to retire')
    parser.add_argument('date', type=str,
                        help='YYYY-MM-DD date to set for legislator end_date')

    args = parser.parse_args()

    settings.update(args)

    retire_legislator(args.leg_id, args.date)


if __name__ == '__main__':
    main()
