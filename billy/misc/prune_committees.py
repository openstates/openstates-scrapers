import argparse
import datetime

from billy import db
from billy.conf import settings, base_arg_parser

def prune_committees(state, remove=False):
    empty_list = []
    old_list = []
    empty_and_old = []
    for com in db.committees.find({'state': state}):
        empty = len(com['members']) == 0
        old = (com['updated_at'] + datetime.timedelta(days=30) < 
               datetime.datetime.utcnow())
        if empty:
            empty_list.append(com)
        if old:
            old_list.append(com)
        if empty and old:
            empty_and_old.append(com)

    print '  %s empty' % len(empty)
    print '  %s not updated in last month' % len(old)
    print '  %s empty & old' % len(empty_and_old)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='prune empty committees',
                                     parents=[base_arg_parser])
    parser.add_argument('states', nargs='+', help='states to validate')
    args = parser.parse_args()
    settings.update(args)

    for state in args.states:
        print "Pruning committees for %s" % state
        prune_committees(state)
