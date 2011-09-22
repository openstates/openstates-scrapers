#!/usr/bin/env python
import csv
import argparse

from billy import db
from billy.utils import metadata, term_for_session
from billy.conf import settings, base_arg_parser


def dump_missing_leg_ids(abbr, detailed=False):
    """
    For a given abbr, find all of the sponsorships, votes and committee
    memberships which are missing legislator IDs and output them to
    CSV files.
    """
    missing_csv = csv.writer(open('%s_missing_leg_ids.csv' % abbr, 'w'))
    missing_csv.writerow(('term', 'chamber', 'name'))
    missing = set()

    level = metadata(abbr)['level']

    if detailed:
        sponsor_csv = csv.writer(open('%s_missing_sponsor_leg_ids.csv' %
                                      abbr, 'w'))
        sponsor_csv.writerow(("Abbreviation", "Session", "Chamber",
                              "Bill ID", "Sponsor Type", "Legislator Name"))

        vote_csv = csv.writer(open("%s_missing_vote_leg_ids.csv" %
                                   abbr, 'w'))
        vote_csv.writerow(("Abbreviation", "Session", "Chamber", "Bill ID",
                           "Vote Index", "Vote Chamber", "Vote Motion",
                           "Vote", "Name"))

    for bill in db.bills.find({'level': level, level: abbr}):
        for sponsor in bill['sponsors']:
            if not sponsor['leg_id']:
                missing.add((term_for_session(abbr, bill['session']),
                             bill['chamber'],
                             sponsor['name'].encode('ascii', 'replace')))

                if detailed:
                    sponsor_csv.writerow((abbr, bill['session'],
                                          bill['chamber'], bill['bill_id'],
                                          sponsor['type'],
                                          sponsor['name'].encode('ascii',
                                                                 'replace')))

        i = 0
        for vote in bill['votes']:
            for vtype in ('yes', 'no', 'other'):
                for v in vote["%s_votes" % vtype]:
                    if not v['leg_id']:
                        missing.add((term_for_session(abbr, bill['session']),
                                     vote['chamber'],
                                     v['name'].encode('ascii', 'replace')))

                        if detailed:
                            vote_csv.writerow((abbr, bill['session'],
                                               bill['chamber'],
                                               bill['bill_id'],
                                               i, vote['chamber'],
                                               vote['motion'], vtype,
                                               v['name'].encode('ascii',
                                                                'replace')))
            i += 1

    if detailed:
        comm_csv = csv.writer(open("%s_missing_committee_leg_ids.csv" %
                                   abbr, 'w'))
        comm_csv.writerow(("Abbreviation", "Chamber", "Committee",
                           "Subcommittee", "Role", "Name"))

    for committee in db.committees.find({'level': level, level: abbr}):
        for member in committee['members']:
            if not member['leg_id']:
                missing.add((committee.get('term', ''),
                             committee['chamber'],
                             member['name'].encode('ascii', 'replace')))

                if detailed:
                    com = committee['committee'].encode('ascii', 'replace')
                    subcom = (committee['subcommittee'] or u'').encode('ascii',
                                                                   'replace')
                    comm_csv.writerow((abbr, committee['chamber'],
                                       com, subcom, member['role'],
                                       member['name'].encode('ascii',
                                                             'replace')))

    for item in missing:
        missing_csv.writerow(item)


def main():
    parser = argparse.ArgumentParser(
        description="dump a CSV of missing leg_id's",
        parents=[base_arg_parser],
    )
    parser.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                        help='data abbreviations to dump')
    parser.add_argument('--detailed', action='store_true', default=False,
                        help='print detailed csvs as well')
    args = parser.parse_args()

    settings.update(args)

    for abbr in args.abbrs:
        dump_missing_leg_ids(abbr, args.detailed)


if __name__ == '__main__':
    main()
