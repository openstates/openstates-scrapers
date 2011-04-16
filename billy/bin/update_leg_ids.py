#!/usr/bin/env python
import argparse
from billy import db
from billy.conf import settings, base_arg_parser
from billy.utils import metadata
from billy.importers.names import NameMatcher


def match_names(state, term):
    nm = NameMatcher(state, term)

    for t in metadata(state)['terms']:
        if t['name'] == term:
            sessions = t['sessions']
            break
    else:
        print 'No such term for %s: %s' % (state, term)
        return

    for session in sessions:
        bills = db.bills.find({'state': state, 'session': session})

        for bill in bills:
            for sponsor in bill['sponsors']:
                if not sponsor['leg_id']:
                    sponsor['leg_id'] = nm.match(sponsor['name'],
                                                 bill['chamber'])
            for vote in bill['votes']:
                for type in ('yes_votes', 'no_votes', 'other_votes'):
                    for voter in vote[type]:
                        if not voter['leg_id']:
                            voter['leg_id'] = nm.match(voter['name'],
                                                       vote['chamber'])
            db.bills.save(bill, safe=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='run name matching against a session',
        parents=[base_arg_parser],
    )

    parser.add_argument('state', help='state to run matching for')
    parser.add_argument('term', help='term to run matching for')

    args = parser.parse_args()

    settings.update(args)

    match_names(args.state, args.term)
