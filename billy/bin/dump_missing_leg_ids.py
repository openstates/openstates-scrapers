#!/usr/bin/env python
import csv
import argparse

from billy import db
from billy.utils import metadata
from billy.conf import settings, base_arg_parser

def _session_to_term(state, session):
    for term in metadata(state)['terms']:
        if session in term['sessions']:
            return term['name']

def dump_missing_leg_ids(state, detailed=False):
    """
    For a given state, find all of the sponsorships, votes and committee
    memberships which are missing legislator IDs and output them to
    CSV files.
    """
    missing_csv = csv.writer(open('%s_missing_leg_ids.csv' % state, 'w'))
    missing_csv.writerow(('state', 'term', 'chamber', 'name'))
    missing = set()

    if detailed:
        sponsor_csv = csv.writer(open('%s_missing_sponsor_leg_ids.csv' %
                                      state, 'w'))
        sponsor_csv.writerow(("State", "Session", "Chamber",
                              "Bill ID", "Sponsor Type", "Legislator Name"))

        vote_csv = csv.writer(open("%s_missing_vote_leg_ids.csv" %
                                   state, 'w'))
        vote_csv.writerow(("State", "Session", "Chamber", "Bill ID",
                           "Vote Index", "Vote Chamber", "Vote Motion",
                           "Vote", "Name"))

    for bill in db.bills.find({'state': state}):
        for sponsor in bill['sponsors']:
            if not sponsor['leg_id']:
                missing.add((bill['state'],
                             _session_to_term(state, bill['session']),
                             bill['chamber'],
                             sponsor['name'].encode('ascii', 'replace')))

                if detailed:
                    sponsor_csv.writerow((state, bill['session'],
                                          bill['chamber'], bill['bill_id'],
                                          sponsor['type'],
                                          sponsor['name'].encode('ascii', 'replace')))

        i = 0
        for vote in bill['votes']:
            for vtype in ('yes', 'no', 'other'):
                for v in vote["%s_votes" % vtype]:
                    if not v['leg_id']:
                        missing.add((bill['state'],
                                     _session_to_term(state, bill['session']),
                                     bill['chamber'],
                                     v['name'].encode('ascii', 'replace')))

                        if detailed:
                            vote_csv.writerow((state, bill['session'],
                                               bill['chamber'],
                                               bill['bill_id'],
                                               i, vote['chamber'],
                                               vote['motion'], vtype,
                                               v['name'].encode('ascii',
                                                                'replace')))
            i += 1

    if detailed:
        comm_csv = csv.writer(open("%s_missing_committee_leg_ids.csv" %
                                   state, 'w'))
        comm_csv.writerow(("State", "Chamber", "Committee", "Subcommittee",
                           "Role", "Name"))

    for committee in db.committees.find({'state': state}):
        for member in committee['members']:
            if not member['leg_id']:
                missing.add((committee['state'], committee.get('term', ''),
                             committee['chamber'],
                             member['name'].encode('ascii', 'replace')))

                if detailed:
                    comm_csv.writerow((state, committee['chamber'],
                                       committee['committee'].encode('ascii', 'replace'),
                                       (committee['subcommittee'] or u'').encode('ascii', 'replace'),
                                       member['role'],
                                       member['name'].encode('ascii', 'replace')))

    for item in missing:
        missing_csv.writerow(item)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="dump a CSV of missing leg_id's",
        parents=[base_arg_parser],
    )
    parser.add_argument('states', metavar='STATE', type=str, nargs='+',
                        help='states to dump')
    args = parser.parse_args()

    settings.update(args)

    for state in args.states:
        dump_missing_leg_ids(state)
