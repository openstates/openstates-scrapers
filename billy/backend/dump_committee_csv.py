import csv
import argparse

import pymongo

from fiftystates import settings
from fiftystates.backend import db

from votesmart import votesmart, VotesmartApiError
votesmart.apikey = getattr(settings, 'VOTESMART_API_KEY', '')

def _extract(d, fields):
    rd = {}
    for f in fields:
        rd[f] = d.get(f, None)
    return rd

def dump_committees(state):
    # votesmart
    vsfields = ('name', 'state', 'type_id', 'committee_id', 'parent' )
    vscsv = csv.DictWriter(open('%s_votesmart_committees.csv' % state, 'w'),
                           vsfields)
    vscsv.writerow(dict(zip(vsfields, vsfields)))

    committees = []
    for type_id in ('H', 'J', 'S'):
        try:
            committees += votesmart.committee.getCommitteesByTypeState(
                type_id, state.upper())
        except VotesmartApiError:
            pass


    committees_by_id = {}
    for c in committees:
        committees_by_id[c.committeeId] = c

    for c in committees:
        d = {'name': c.name, 'state': c.stateId,
             'type_id': c.committeetypeId, 'committee_id':c.committeeId,
             'parent': committees_by_id.get(c.parentId, None)}
        vscsv.writerow(d)

    # write committees from db
    db.committees.ensure_index([('state', pymongo.ASCENDING),
                                ('chamber', pymongo.ASCENDING)])
    db.committees.ensure_index([('state', pymongo.ASCENDING),
                                ('votesmart_id', pymongo.ASCENDING)])

    fields = ('_id', 'chamber', 'committee', 'subcommittee', 'votesmart_id',)
    writer = csv.DictWriter(open(state+'_committees.csv', 'w'), fields)

    writer.writerow(dict(zip(fields, fields)))

    for c in db.committees.find({'state':state}):
        writer.writerow(_extract(c, fields))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='get two CSVs of committee data'
    )

    parser.add_argument('states', metavar='STATE', type=str, nargs='+',
                        help='states to dump')
    parser.add_argument('--votesmart_key', type=str,
                        help='the Project Vote Smart API key to use')

    args = parser.parse_args()

    if args.votesmart_key:
        votesmart.apikey = args.votesmart_key

    for state in args.states:
        dump_committees(state)
