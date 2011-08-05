import argparse
import datetime

from billy import db
from billy.conf import settings, base_arg_parser

def prune_committees(state, remove=False):
    empty_and_old = []
    for com in db.committees.find({'state': state}):
        empty = len(com['members']) == 0
        old = (com['updated_at'] + datetime.timedelta(days=30) < 
               datetime.datetime.utcnow())
        if empty and old:
            empty_and_old.append(com)

    print '  %s to prune' % len(empty_and_old)
    if remove:
        for c in empty_and_old:
            db.committees.remove(c['_id'])
        print 'deleted'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='prune empty committees',
                                     parents=[base_arg_parser])
    parser.add_argument('states', nargs='*', help='states to validate')
    parser.add_argument('--all', action='store_true', default=False,
                        help='prune all states')
    parser.add_argument('--delete', action='store_true', default=False,
                        help='actually delete committees')
    args = parser.parse_args()
    settings.update(args)

    if args.all:
        args.states = db.metadata.find().distinct('_id')

    if not args.states:
        print "Must specify at least one state or --all"

    for state in args.states:
        print "Pruning committees for %s" % state
        prune_committees(state, args.delete)
