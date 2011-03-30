#!/usr/bin/env python

import os
import csv
import argparse
from collections import defaultdict

from billy import db
from billy.conf import settings, base_arg_parser
from billy.utils import metadata

def categorize_subjects(state, data_dir, process_all):
    categorizer = defaultdict(set)
    categories_per_bill = defaultdict(int)
    uncategorized = defaultdict(int)

    filename = os.path.join(data_dir, state+'.csv')
    try:
        reader = csv.reader(open(filename))

        # build category mapping
        for row in reader:
            for subj in row[1:]:
                if subj:
                    if subj not in settings.BILLY_SUBJECTS:
                        raise Exception('invalid subject %s (%s)' % (subj, row[0]))
                    categorizer[row[0]].add(subj)
    except IOError:
        print 'Proceeding without', filename

    spec = {'state':state}
    if not process_all:
        sessions = metadata(state)['terms'][-1]['sessions']
        spec['session'] = {'$in': sessions}

    for bill in db.bills.find(spec):
        subjects = set()
        for ss in bill.get('scraped_subjects', []):
            categories = categorizer[ss]
            if not categories:
                uncategorized[ss] += 1
            subjects.update(categories)
        bill['subjects'] = list(subjects)

        # increment # of bills with # of subjects
        categories_per_bill[len(subjects)] += 1

        db.bills.save(bill)

    print 'Categories per bill'
    print '-------------------'
    for ncats, total in sorted(categories_per_bill.items()):
        print '%s categories: %s bills' % (ncats, total)

    print 'Uncategorized'
    print '-------------'
    subjects_i = sorted([(v,k) for k,v in uncategorized.items()], reverse=True)
    for n, category in subjects_i:
        print '%s,%s' % (n, category)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='apply subject categorization for bills for a given state',
        parents=[base_arg_parser],
        conflict_handler='resolve',
    )

    default_dir = os.path.join(os.path.dirname(__file__),
                           '../../manual_data/subjects')

    parser.add_argument('state', type=str, help='state to process')
    parser.add_argument('--all', help='update all sessions',
                        action='store_true', default=False)
    parser.add_argument('-d', '--data_dir', help='directory of subject csvs',
                        dest='data_dir', default=default_dir)
    args = parser.parse_args()

    settings.update(args)

    categorize_subjects(args.state, args.data_dir, args.all)
