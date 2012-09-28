#!/usr/bin/env python
import os
import csv
import sys
import tempfile
import subprocess

from billy import db, utils
from billy.core import settings


def vote_csv(abbr, session, chamber, out=sys.stdout):
    term = utils.term_for_session(abbr, session)

    votes = {}
    legislators = {}

    elemMatch = {settings.LEVEL_FIELD: abbr, 'chamber': chamber,
                 'type': 'member', 'term': term}

    for leg in db.legislators.find({'$or':
                                    [{'roles': {'$elemMatch': elemMatch}},
                                     {('old_roles.%s' % term):
                                      {'$elemMatch': elemMatch}}]}):
        votes[leg['leg_id']] = []
        legislators[leg['leg_id']] = leg

    for bill in db.bills.find({settings.LEVEL_FIELD: abbr, 'chamber': chamber,
                               'session': session}):
        for vote in bill['votes']:
            if 'committee' in vote and vote['committee']:
                continue
            if vote['chamber'] != chamber:
                continue

            seen = set()

            for yv in vote['yes_votes']:
                leg_id = yv['leg_id']
                if leg_id:
                    seen.add(leg_id)
                    try:
                        votes[leg_id].append(1)
                    except KeyError:
                        continue
            for nv in vote['no_votes']:
                leg_id = nv['leg_id']
                if leg_id:
                    seen.add(leg_id)
                    try:
                        votes[leg_id].append(6)
                    except KeyError:
                        continue

            for leg_id in set(votes.keys()) - seen:
                votes[leg_id].append(9)

    out = csv.writer(out)

    for (leg_id, vs) in votes.iteritems():
        leg = legislators[leg_id]

        try:
            party = leg['old_roles'][term][0]['party']
        except KeyError:
            party = leg['party']

        row = [leg['full_name'].encode('ascii', 'replace'), leg['leg_id'],
               party]
        for vote in vs:
            row.append(str(vote))

        out.writerow(row)


def wnominate(abbr, session, chamber, polarity, r_bin="R",
              out_file=None):
    (fd, filename) = tempfile.mkstemp('.csv')
    with os.fdopen(fd, 'w') as out:
        vote_csv(abbr, session, chamber, out)

    if not out_file:
        (result_fd, out_file) = tempfile.mkstemp('.csv')
        os.close(result_fd)

    r_src_path = os.path.join(os.path.dirname(__file__), 'calc_wnominate.R')

    with open('/dev/null', 'w') as devnull:
        subprocess.check_call([r_bin, "-f", r_src_path, "--args",
                               filename, out_file, polarity],
                              stdout=devnull, stderr=devnull)

    results = {}
    with open(out_file) as f:
        c = csv.DictReader(f)
        for row in c:
            try:
                res = float(row['coord1D'])
            except ValueError:
                res = None
            results[row['leg_id']] = res

    os.remove(filename)

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('abbr')
    parser.add_argument('session')
    parser.add_argument('chamber')
    parser.add_argument('polarity')
    parser.add_argument('out_file')
    args = parser.parse_args()

    wnominate(args.abbr, args.session, args.chamber, args.polarity,
              out_file=args.out_file)
