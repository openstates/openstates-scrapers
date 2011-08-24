import csv
import argparse
from collections import defaultdict

from billy import db
from billy.conf import settings, base_arg_parser


def keyfunc(x):
    try:
        district = int(x[2])
    except ValueError:
        district = x[2]
    return x[1], district


def generate_csv(state):
    fields = ('abbr', 'chamber', 'name', 'num_seats')
    out = csv.writer(open(state+'_districts.csv', 'w'))
    out.writerow(fields)

    counts = defaultdict(int)
    for leg in db.legislators.find({'state': state, 'active': True}):
        if 'chamber' in leg:
            counts[(state, leg['chamber'], leg['district'])] += 1

    data = []
    for key, count in counts.iteritems():
        state, chamber, district =  key
        data.append((state, chamber, district, count))

    data.sort(key=keyfunc)

    for item in data:
        out.writerow(item)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='generate district CSV files',
                                     parents=[base_arg_parser])
    parser.add_argument('states', nargs='*', help='states to validate')
    parser.add_argument('--all', action='store_true', default=False,
                        help='generate csv for all states')
    args = parser.parse_args()
    settings.update(args)

    if args.all:
        args.states = db.metadata.find().distinct('_id')

    if not args.states:
        print "Must specify at least one state or --all"

    for state in args.states:
        print "Generating District CSV for %s" % state
        generate_csv(state)
