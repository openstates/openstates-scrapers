#!/usr/bin/env python

import os
import csv
import argparse
from collections import defaultdict

from billy import db
from billy.utils import metadata

SUBJECTS = ['Agriculture and Food',
            'Animal Rights and Wildlife Issues',
            'Arts and Humanities',
            'Budget, Spending, and Taxes',
            'Business and Consumers',
            'Campaign Finance and Election Issues',
            'Civil Liberties and Civil Rights',
            'Commerce',
            'Crime',
            'Drugs',
            'Education',
            'Energy',
            'Environmental',
            'Executive Branch',
            'Family and Children Issues',
            'Federal, State, and Local Relations',
            'Gambling and Gaming',
            'Government Reform',
            'Guns',
            'Health',
            'Housing and Property',
            'Immigration',
            'Indigenous Peoples',
            'Insurance',
            'Judiciary',
            'Labor and Employment',
            'Legal Issues',
            'Legislative Affairs',
            'Military',
            'Municipal and County Issues',
            'Other',
            'Public Services',
            'Recreation',
            'Reproductive Issues',
            'Resolutions',
            'Science and Medical Research',
            'Senior Issues',
            'Sexual Orientation and Gender Issues',
            'Social Issues',
            'State Agencies',
            'Technology and Communication',
            'Trade',
            'Transportation',
            'Welfare and Poverty']

def categorize_subjects(state, data_dir, process_all):
    categorizer = defaultdict(set)
    categories_per_bill = defaultdict(int)
    uncategorized = defaultdict(int)

    reader = csv.reader(open(os.path.join(data_dir, state+'.csv')))

    # build category mapping
    for row in reader:
        for subj in row[1:]:
            if subj:
                if subj not in SUBJECTS:
                    raise Exception('invalid subject %s (%s)' % (subj, row[0]))
                categorizer[row[0]].add(subj)


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
    )

    default_dir = os.path.join(os.path.dirname(__file__),
                           '../manual_data/subjects')

    parser.add_argument('state', type=str, help='state to process')
    parser.add_argument('-d', type=str, help='directory of subject csvs',
                        dest='data_dir', default=default_dir)
    parser.add_argument('--all', help='update all sessions',
                        action='store_true', default=False)
    args = parser.parse_args()

    categorize_subjects(args.state, args.data_dir, args.all)
