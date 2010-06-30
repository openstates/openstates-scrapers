#!/usr/bin/env python
import sys

from fiftystates import settings
from fiftystates.backend import db
from fiftystates.backend.utils import base_arg_parser

import argparse
import name_tools
from nimsp import nimsp, NimspApiError

nimsp.apikey = getattr(settings, 'NIMSP_API_KEY', '')


def import_nimsp_ids(state_abbrev):
    state_abbrev = state_abbrev.lower()
    state = db.metadata.find_one({'_id': state_abbrev})
    if not state:
        print "State '%s' does not exist in the database." % state_abbrev
        sys.exit(1)

    upper_office_id = 'S00'
    if state['lower_chamber_name'].startswith('House'):
        lower_office_id = 'R00'
    elif state['lower_chamber_name'].startswith('Assembly'):
        lower_office_id = 'R01'
    else:
        lower_office_id = None

    current_session = state['sessions'][-1]['name']
    year = state['sessions'][-1]['start_year'] - 1

    for leg in db.legislators.find({'roles': {'$elemMatch': {
                    'type': 'member',
                    'session': current_session,
                    'state': state_abbrev}}}):

        role = None
        for r in leg['roles']:
            if r['type'] == 'member' and r['session'] == current_session:
                role = r
                break

        office_id = {'upper': upper_office_id,
                     'lower': lower_office_id}[role['chamber']]

        # NIMSP is picky about name format
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
            db.legislators.save(leg)
        else:
            print "Too many results for %s" % name.encode('asii', 'replace')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        parents=[base_arg_parser],
        description=('Associate Fifty State objects with corresponding '
                     'National Institute on Money in State Politics IDs.'))

    parser.add_argument('--nimsp_key', '-k', type=str,
                        help='the NIMSP API key to use')

    args = parser.parse_args()

    if args.nimsp_key:
        nimsp.apikey = args.nimsp_key

    import_nimsp_ids(args.state)
