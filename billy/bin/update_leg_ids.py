#!/usr/bin/env python
import argparse
from billy import db
from billy.conf import settings, base_arg_parser
from billy.utils import metadata
from billy.importers.names import NameMatcher


def match_names(abbr, term):
    level = metadata(abbr)['level']
    nm = NameMatcher(abbr, term, level)

    for t in metadata(abbr)['terms']:
        if t['name'] == term:
            sessions = t['sessions']
            break
    else:
        print 'No such term for %s: %s' % (abbr, term)
        return

    for session in sessions:
        bills = db.bills.find({'level': level, level: abbr,
                               'session': session})

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


def main():
    parser = argparse.ArgumentParser(
        description='run name matching against a session',
        parents=[base_arg_parser],
    )

    parser.add_argument('abbr', help='abbr to run matching for')
    parser.add_argument('term', help='term to run matching for')

    args = parser.parse_args()

    settings.update(args)

    match_names(args.abbr, args.term)


if __name__ == '__main__':
    main()
