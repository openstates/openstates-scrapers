#!/usr/bin/env python

from billy import db
from billy.conf import settings, base_arg_parser
import csv
import argparse


def process_file(state, save=False):

    filename = state + '_legislators.csv'

    # print initial missing counts
    print 'missing pvs', db.legislators.find({'state': state,
                                              'votesmart_id': None}).count()
    print 'missing tdata', db.legislators.find({'state': state,
                                        'transparencydata_id': None}).count()

    namefile = csv.DictReader(open(filename))

    for row in namefile:
        # get the legislator
        leg = db.legislators.find_one({'leg_id': row['leg_id']})
        if not leg:
            print 'no such leg:', row['leg_id']
            continue

        # backwards compatibility, copy full_name into _scraped_name
        if '_scraped_name' not in leg:
            leg['_scraped_name'] = leg['full_name']

        # check columns
        changed = {}
        keys = set(['first_name', 'middle_name', 'last_name', 'suffixes',
                   'nickname', 'votesmart_id', 'transparencydata_id',
                   'photo_url'])
        keys.intersection_update(namefile.fieldnames)
        for key in keys:
            row[key] = row[key].decode('utf-8')
            fileval = (row[key] or u'').strip()
            dbval = leg.get(key, '').strip()
            if fileval != dbval:
                changed[key] = dbval
                leg[key] = fileval
            if key in leg:
                leg[key] = leg[key].strip()

        # show what changed
        if changed:
            print row['leg_id']
            for k, v in changed.iteritems():
                print '  %s [%s --> %s]' % (k, v, row[k])

        # reassemble full_name
        full_name = leg['first_name']
        #if leg.get('nickname'):
        #    full_name += ' "%s"' % leg['nickname']
        if leg['middle_name']:
            full_name += u' %s' % leg['middle_name']
        full_name += u' %s' % leg['last_name']
        if leg['suffixes']:
            full_name += u' %s' % leg['suffixes']
        leg['full_name'] = full_name

        if save:
            locked = list(set(leg.get('_locked_fields', []) +
                              changed.keys() + ['full_name']))
            leg['_locked_fields'] = locked
            db.legislators.save(leg, safe=True)

    if save:
        print 'missing pvs', db.legislators.find({'state': state,
                                          'votesmart_id': None}).count()
        print 'missing tdata', db.legislators.find({'state': state,
                                    'transparencydata_id': None}).count()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='load a CSV of legislator data',
        parents=[base_arg_parser],
    )

    parser.add_argument('states', metavar='STATE', type=str, nargs='+',
                help='states to load (filenames should be xy_legislators.csv)')
    parser.add_argument('--save', action='store_true', default=False,
                        help='save changes to database')

    args = parser.parse_args()

    settings.update(args)

    for state in args.states:
        process_file(state, args.save)
