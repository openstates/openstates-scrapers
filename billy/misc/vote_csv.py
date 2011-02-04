import csv
import sys

from billy import db, utils


def vote_csv(state, session, chamber):
    term = utils.term_for_session(state, session)

    votes = {}
    legislators = {}

    elemMatch = {'state': state, 'chamber': chamber,
                 'type': 'member', 'term': term}

    for leg in db.legislators.find({'$or':
                                    [{'roles': {'$elemMatch': elemMatch}},
                                     {('old_roles.%s' % term):
                                      {'$elemMatch': elemMatch}}]}):
        votes[leg['leg_id']] = []
        legislators[leg['leg_id']] = leg

    for bill in db.bills.find({'state': state, 'chamber': chamber,
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

    out = csv.writer(sys.stdout)

    for (leg_id, vs) in votes.iteritems():
        leg = legislators[leg_id]

        try:
            party = leg['old_roles'][session][0]['party']
        except KeyError:
            party = leg['party']

        row = [leg['full_name'], party]
        for vote in vs:
            row.append(str(vote))

        out.writerow(row)


if __name__ == '__main__':
    state = sys.argv[1]
    session = sys.argv[2]
    chamber = sys.argv[3]

    vote_csv(state, session, chamber)
