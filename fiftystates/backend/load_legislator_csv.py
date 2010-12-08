#!/usr/bin/env python

from fiftystates.backend import db
import csv

def process_file(filename, save=False):

    # print initial missing counts
    print 'missing pvs', db.legislators.find({'state':state,
                                              'votesmart_id':None}).count()
    print 'missing tdata', db.legislators.find({'state':state,
                                        'transparencydata_id':None}).count()

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
        changed = []
        keys = ('first_name', 'middle_name', 'last_name', 'suffixes',
                'nickname', 'votesmart_id', 'transparencydata_id')
        for key in keys:
            fileval = (row[key] or '').strip()
            dbval = leg.get(key, '')
            if fileval != dbval:
                leg[key] = fileval
                changed.append(key)
            if key in leg:
                leg[key] = leg[key].strip()

        # show what changed
        if changed:
            print row['leg_id'], 'changed', ' '.join(changed)

        # reassemble full_name
        full_name = leg['first_name']
        #if leg.get('nickname'):
        #    full_name += ' "%s"' % leg['nickname']
        if leg['middle_name']:
            full_name += ' %s' % leg['middle_name']
        full_name += ' %s' % leg['last_name']
        if leg['suffixes']:
            full_name += ' %s' % leg['suffixes']
        leg['full_name'] = full_name

        if save:
            locked = list(set(leg.get('_locked_fields', []) +
                              changed + ['full_name']))
            leg['_locked_fields'] = locked
            db.legislators.save(leg, safe=True)

            print 'missing pvs', db.legislators.find({'state':state,
                                              'votesmart_id':None}).count()
            print 'missing tdata', db.legislators.find({'state':state,
                                        'transparencydata_id':None}).count()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='load a CSV of legislator data'
    )

    parser.add_argument('files', metavar='FILE', type='str', nargs='+',
                        help='state files to load')
    parser.add_argument('--save', action='store_true', default=False,
                        help='save changes to database')

    args = parser.parse_args()

    for filename in args.files:
        process_file(filename, args.save)
