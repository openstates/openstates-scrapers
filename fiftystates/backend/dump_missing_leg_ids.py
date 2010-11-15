#!/usr/bin/env python
import csv
import argparse

from fiftystates.backend import db


def dump_missing_leg_ids(state):
    """
    For a given state, find all of the sponsorships, votes and committee
    memberships which are missing legislator IDs and output them to
    CSV files.
    """
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
                sponsor_csv.writerow((state, bill['session'],
                                      bill['chamber'], bill['bill_id'],
                                      sponsor['type'], sponsor['name']))

        i = 0
        for vote in bill['votes']:
            for vtype in ('yes', 'no', 'other'):
                for v in vote["%s_votes" % vtype]:
                    if not v['leg_id']:
                        vote_csv.writerow((state, bill['session'],
                                           bill['chamber'], bill['bill_id'],
                                           i, vote['chamber'],
                                           vote['motion'], vtype,
                                           v['name'].encode('ascii',
                                                            'replace')))
            i += 1

    comm_csv = csv.writer(open("%s_missing_committee_leg_ids.csv" %
                               state, 'w'))
    comm_csv.writerow(("State", "Chamber", "Committee", "Subcommittee",
                       "Role", "Name"))

    for committee in db.committees.find({'state': state}):
        for member in committee['members']:
            if not member['leg_id']:
                comm_csv.writerow((state, committee['chamber'],
                                   committee['committee'],
                                   committee['subcommittee'],
                                   member['role'], member['name']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="dump a CSV of missing leg_id's")
    parser.add_argument('states', metavar='STATE', type=str, nargs='+',
                        help='states to dump')
    args = parser.parse_args()

    for state in args.states:
        dump_missing_leg_ids(state)
