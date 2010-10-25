from fiftystates import settings
from fiftystates.backend import db

import argparse
import name_tools
import pymongo

from nimsp import nimsp, NimspApiError
nimsp.apikey = getattr(settings, 'NIMSP_API_KEY', '')

from votesmart import votesmart, VotesmartApiError
votesmart.apikey = getattr(settings, 'VOTESMART_API_KEY', '')

def update_nimsp_ids(state):
    state_abbrev = state['abbreviation']

    office_ids = {'upper': 'S00'}
    upper_office_id = 'S00'
    if state['lower_chamber_name'].startswith('House'):
        office_ids['lower'] = 'R00'
    else:
        office_ids['lower'] = 'R01'

    current_term = state['terms'][-1]['name']
    year = state['terms'][-1]['start_year'] - 1

    query = {'roles':
             {'$elemMatch': {
                'type': 'member',
                'term': current_term,
                'state': state_abbrev}},
             'nimsp_candidate_id': None,
    }

    initial_count = db.legislators.find(query).count()
    update_count = 0

    for leg in db.legislators.find(query):
        role = None
        for r in leg['roles']:
            if r['type'] == 'member' and r['term'] == current_term:
                role = r
                break

        office_id = office_ids[role['chamber']]

        # NIMSP is picky about LAST, FIRST name format
        name = leg['last_name']
        if 'suffix' in leg and leg['suffix']:
            name += " " + leg['suffix'].replace(".", "")
        name += ", " + leg['first_name'].replace(".", "")

        try:
            results = nimsp.candidates.list(
                state=state_abbrev, office=office_id,
                candidate_name=name, year=year,
                candidate_status='WON')
        except NimspApiError as e:
            print "Failed matching %s" % name.encode('ascii', 'replace')
            continue

        if len(results) == 1:
            leg['nimsp_candidate_id'] = int(
                results[0].imsp_candidate_id)
            db.legislators.save(leg, safe=True)
            update_count += 1
        else:
            print "Too many results for %s" % name.encode('ascii', 'replace')

    print 'Updated %s of %s missing NIMSP ids' % (update_count, initial_count)


def update_votesmart_committees(state):
    db.committees.ensure_index([('state', pymongo.ASCENDING),
                                ('chamber', pymongo.ASCENDING)])
    db.committees.ensure_index([('state', pymongo.ASCENDING),
                                ('votesmart_id', pymongo.ASCENDING)])

    types = {'upper': 'S'}
    if 'lower_chamber_name' in state:
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


def update_votesmart_legislators(state):
    current_term = state['terms'][-1]['name']

    query = {'roles': {'$elemMatch':
                       {'type': 'member',
                        'state': state['abbreviation'],
                        'term': current_term}
                      },
             'votesmart_id': None,
            }

    print '%s without votesmart id' % db.legislators.find(query).count()

    upper_officials = votesmart.officials.getByOfficeState(9,
                                                       state['_id'].upper())

    try:
        lower_officials = votesmart.officials.getByOfficeState(8,
                                                          state['_id'].upper())
    except VotesmartApiError:
        lower_officials = votesmart.officials.getByOfficeState(7,
                                                          state['_id'].upper())

    def _match(chamber, vsofficials):
        for unmatched in db.legislators.find(dict(query, chamber=chamber)):
            print unmatched['district']
            for vso in vsofficials:
                if (unmatched['district'] == vso.officeDistrictName and
                    unmatched['last_name'] == vso.lastName):
                    unmatched['votesmart_id'] = vso.candidateId
                    db.legislators.save(unmatched, safe=True)

    _match('upper', upper_officials)
    _match('lower', lower_officials)

    print '%s without votesmart id' % db.legislators.find(query).count()



def update_missing_ids(state_abbrev):
    state = db.metadata.find_one({'_id': state_abbrev.lower()})
    if not state:
        print "State '%s' does not exist in the database." % (
            state_abbrev)
        sys.exit(1)

    #print "Updating NIMSP ids..."
    #update_nimsp_ids(state)

    #print "Updating PVS committee ids..."
    #update_votesmart_committees(state)

    print "Updating PVS legislator ids..."
    update_votesmart_legislators(state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        add_help=False,
        description=('attempt to match legislators with ids in other'
                     'relevant APIs'))

    parser.add_argument('states', metavar='STATE', type=str, nargs='+',
                        help='states to update')
    parser.add_argument('--nimsp_key', type=str,
                        help='the NIMSP API key to use')
    parser.add_argument('--votesmart_key', type=str,
                        help='the Project Vote Smart API key to use')

    args = parser.parse_args()

    if args.nimsp_key:
        nimsp.apikey = args.nimsp_key
    if args.votesmart_key:
        votesmart.apikey = args.votesmart_key

    for state in args.states:
        update_missing_ids(state)

