#!/usr/bin/env python

from fiftystates import settings
from fiftystates.backend import db

import re
import datetime

import argparse
import name_tools
import pymongo

from nimsp import nimsp, NimspApiError
nimsp.apikey = getattr(settings, 'NIMSP_API_KEY', '')

from votesmart import votesmart, VotesmartApiError
votesmart.apikey = getattr(settings, 'VOTESMART_API_KEY', '')

def _nimspize(iid):
    match = re.match('(\d+)(.*)', iid)
    if match:
        n, rest = match.groups()
        return '%03d%s' % (int(n), rest)
    else:
        return iid

def update_nimsp_ids(state):

    abbrev = state['abbreviation']
    current_term = state['terms'][-1]['name']

    # the year calculation can be quite difficult. generally the story is that
    # it'll be start_year-term.  but some states (NJ in particular) complicate
    # the story by having variable terms

    # the result? a fairly nasty hack

    # start last year and try walking backwards
    year = datetime.datetime.today().year - 1
    upper_cands = lower_cands = None

    # try and get lower_cands walking backwards one year at a time
    while not lower_cands:
        try:
            lower_cands = nimsp.candidates.list(state=abbrev, office='R00',
                                                year=year,
                                                candidate_status='Won')
        except NimspApiError:
            try:
                lower_cands = nimsp.candidates.list(state=abbrev, office='R01',
                                                    year=year,
                                                    candidate_status='Won')
            except NimspApiError:
                year -= 1

    # do the same thing for upper_cands
    while not upper_cands:
        try:
            upper_cands = nimsp.candidates.list(state=abbrev, office='S00',
                                                year=year,
                                                candidate_status='Won')
        except NimspApiError:
            year -= 1


    query = {'roles':
             {'$elemMatch': {
                'type': 'member',
                'term': current_term,
                'state': abbrev}},
             'nimsp_candidate_id': None,
    }

    initial_count = db.legislators.find(query).count()

    def _match(chamber, candidates):
        updated = 0
        for leg in db.legislators.find(dict(query, chamber=chamber)):
            for cand in candidates:
                if (cand.candidate_name.startswith(leg['last_name'].upper())
                    and (_nimspize(leg['district']) == cand.district)):
                    leg['nimsp_candidate_id'] = cand.imsp_candidate_id
                    db.legislators.save(leg, safe=True)
                    updated += 1
        return updated

    updated = _match('upper', upper_cands)
    updated += _match('lower', lower_cands)

    print 'Updated %s of %s missing NIMSP ids' % (updated, initial_count)

def update_votesmart_legislators(state):
    current_term = state['terms'][-1]['name']

    query = {'roles': {'$elemMatch':
                       {'type': 'member',
                        'state': state['abbreviation'],
                        'term': current_term}
                      },
             'votesmart_id': None,
            }

    updated = 0
    initial_count = db.legislators.find(query).count()

    # get officials
    abbrev = state['_id'].upper()
    upper_officials = votesmart.officials.getByOfficeState(9, abbrev)
    try:
        lower_officials = votesmart.officials.getByOfficeState(8, abbrev)
    except VotesmartApiError:
        lower_officials = votesmart.officials.getByOfficeState(7, abbrev)

    def _match(chamber, vsofficials):
        updated = 0
        for unmatched in db.legislators.find(dict(query, chamber=chamber)):
            for vso in vsofficials:
                if (unmatched['district'] == vso.officeDistrictName and
                    unmatched['last_name'] == vso.lastName):
                    unmatched['votesmart_id'] = vso.candidateId
                    db.legislators.save(unmatched, safe=True)
                    updated += 1
        return updated

    updated += _match('upper', upper_officials)
    updated += _match('lower', lower_officials)

    print 'Updated %s of %s missing votesmart ids' % (updated, initial_count)



def update_missing_ids(state_abbrev):
    state = db.metadata.find_one({'_id': state_abbrev.lower()})
    if not state:
        print "State '%s' does not exist in the database." % (
            state_abbrev)
        sys.exit(1)

    print "Updating NIMSP ids..."
    update_nimsp_ids(state)

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

