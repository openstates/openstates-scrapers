#!/usr/bin/env python

from fiftystates import settings
from fiftystates.backend import db

import re
import json
import urllib, urllib2
import datetime

import argparse
import name_tools
import pymongo

from votesmart import votesmart, VotesmartApiError
votesmart.apikey = getattr(settings, 'VOTESMART_API_KEY', '')

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

def update_transparencydata_legislators(state, sunlight_key):
    current_term = state['terms'][-1]['name']
    # here we are querying roles
    query = {'roles': {'$elemMatch':
                       {'type': 'member',
                        'state': state['abbreviation'],
                        'term': current_term}
                      },
             'transparencydata_id': None,
             'active': True,
            }

    updated = 0
    initial_count = db.legislators.find(query).count()
    state_abbrev = state['_id'].upper()

    for leg in db.legislators.find(query):
        query = urllib.urlencode({'apikey': sunlight_key,
                                  'search': leg['full_name'].encode('utf8')})
	url = 'http://transparencydata.com/api/1.0/entities.json?' + query
        data = urllib2.urlopen(url).read()
        results = json.loads(data)
        matches = []
        # here we were trying to match against the person's chamber
        # as opposed to the role's chamber
        # was leg['chamber']
        # should be leg['roles'][0]['chamber']
        # because there is no guarantee that a given person will have a
        # chamber atrribute
        for result in results:
            if (result['state'] == state_abbrev and
                result['seat'][6:] == leg['roles'][0]['chamber'] and
                result['type'] == 'politician'):
                matches.append(result)
        if len(matches) == 1:
            leg['transparencydata_id'] = matches[0]['id']
            db.legislators.save(leg, safe=True)
            updated += 1

    print 'Updated %s of %s missing transparencydata ids' % (updated, initial_count)


def update_missing_ids(state_abbrev, sunlight_key):
    state = db.metadata.find_one({'_id': state_abbrev.lower()})
    if not state:
        print "State '%s' does not exist in the database." % (
            state_abbrev)
        sys.exit(1)

    print "Updating PVS legislator ids..."
    update_votesmart_legislators(state)

    print "Updating TransparencyData ids..."
    update_transparencydata_legislators(state, sunlight_key)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        add_help=False,
        description=('attempt to match legislators with ids in other'
                     'relevant APIs'))

    parser.add_argument('states', metavar='STATE', type=str, nargs='+',
                        help='states to update')
    parser.add_argument('--votesmart_key', type=str,
                        help='the Project Vote Smart API key to use')
    parser.add_argument('--sunlight_key', type=str,
                        help='the Sunlight API key to use')

    args = parser.parse_args()

    if args.votesmart_key:
        votesmart.apikey = args.votesmart_key
    if args.sunlight_key:
        sunlight_key = args.sunlight_key
    else:
        sunlight_key = None

    for state in args.states:
        update_missing_ids(state, sunlight_key)

