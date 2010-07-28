#!/usr/bin/env python
import re
import sys

from fiftystates import settings
from fiftystates.backend import db
from fiftystates.backend.utils import insert_with_id, base_arg_parser

import pymongo
import argparse
from votesmart import votesmart, VotesmartApiError

votesmart.apikey = getattr(settings, 'VOTESMART_API_KEY', '')


def import_votesmart_data(state_abbrev):
    state = db.metadata.find_one({'_id': state_abbrev.lower()})
    if not state:
        print "State '%s' does not exist in the database." % (
            state_abbrev)
        sys.exit(1)

    print "Syncing committees..."
    import_committees(state)

    print "Syncing legislator IDs..."
    import_legislator_ids(state)


def import_committees(state):
    db.committees.ensure_index([('state', pymongo.ASCENDING),
                                ('chamber', pymongo.ASCENDING)])
    db.committees.ensure_index([('state', pymongo.ASCENDING),
                                ('votesmart_id', pymongo.ASCENDING)])

    types = {'upper': 'S'}
    if state['lower_chamber_name'].startswith('House'):
        types['lower'] = 'H'
    else:
        types['lower'] = 'S'

    for chamber, typeId in types.items():
        for committee in votesmart.committee.getCommitteesByTypeState(
            typeId=typeId, stateId=state['_id'].upper()):

            committee_name = committee.name
            subcommittee_name = None

            if committee.parentId != "-1":
                parent = votesmart.committee.getCommittee(committee.parentId)
                subcommittee_name = committee_name
                committee_name = parent.name

            spec = {'state': state['_id'],
                    'chamber': chamber,
                    'committee': committee_name}
            if subcommittee_name:
                spec['subcommittee'] = subcommittee_name

            data = db.committees.find_one(spec)

            if not data:
                print "No matches for '%s'" % (subcommittee_name or
                                               committee_name)
                continue

            data['votesmart_id'] = committee.committeeId

            db.committees.save(data, safe=True)


def import_committee_ids(state):
    for legislator in db.legislators.find({'state': state['_id']}):
        for role in legislator['roles']:
            if role['type'] == 'committee member':
                comms = db.committees.find({
                        'state': state['_id'],
                        'name': role['committee']})

                if comms.count() != 1:
                    print comms.count()
                    print "couldn't find '%s'" % role['committee']
                    continue

                role['committee_votesmart_id'] = comms[0]['votesmart_id']


def import_legislator_ids(state):
    offices = {'upper': 9}
    if state['lower_chamber_name'].startswith('House'):
        offices['lower'] = 8
    else:
        offices['lower'] = 7

    current_term = state['terms'][-1]['name']

    for chamber, office in offices.items():
        officials = votesmart.officials.getByOfficeState(
            office, state['_id'].upper())

        for official in officials:
            legs = db.legislators.find(
                {'roles': {'$elemMatch':
                     {'type': 'member',
                      'chamber': chamber,
                      'district': official.officeDistrictName,
                      'term': current_term}},
                 'last_name': official.lastName,
               })

            if legs.count() > 1:
                print ("Too many matches for '%s'" % official).encode(
                    'ascii', 'replace')
            elif legs.count() == 0:
                print ("No matches for '%s'" % official).encode('ascii',
                                                                'replace')
            else:
                leg = legs[0]

                for r in leg['roles']:
                    if (r['type'] == 'member' and
                        r['term'] == current_term):

                        leg['votesmart_id'] = official.candidateId
                        db.legislators.save(leg, safe=True)

                        break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        parents=[base_arg_parser],
        description=('Associate Fifty State objects with corresponding '
                     'Project Vote Smart IDs.'))

    parser.add_argument('--votesmart_key', '-k', type=str,
                        help='the votesmart API key to use')

    args = parser.parse_args()

    if args.votesmart_key:
        votesmart.apikey = args.votesmart_key

    import_votesmart_data(args.state)
