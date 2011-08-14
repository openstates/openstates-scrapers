import argparse
from collections import defaultdict

from billy import db
from billy.conf import settings, base_arg_parser


def all_actions(state):
    actions = defaultdict(lambda: defaultdict(int))

    bills = db.bills.find({'state':state}, {'actions':1})
    for bill in bills:
        for action in bill['actions']:
            for atype in action['type']:
                actions[atype][action['action']] += 1

    return actions


def action_report(state, threshold=10):
    adict = all_actions(state)

    totals = defaultdict(int)
    for atype, actions in adict.iteritems():
        print atype, sum(actions.values())

        for act, count in sorted(actions.iteritems(), key=lambda x: x[1],
                                 reverse=True):
            if count > threshold:
                print '  ',act.encode('utf-8','ignore'), count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='generate action report',
                                     parents=[base_arg_parser])
    parser.add_argument('state', help='state to generate report for')
    parser.add_argument('--threshold', type=int, default=5,
                        help='only report actions occuring this many times')
    args = parser.parse_args()
    settings.update(args)

    action_report(args.state, args.threshold)
