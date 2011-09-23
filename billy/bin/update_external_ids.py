#!/usr/bin/env python

from billy.conf import settings, base_arg_parser
from billy import db

import sys
import json
import urllib
import urllib2
import time

import argparse

from votesmart import votesmart, VotesmartApiError


def update_votesmart_legislators(meta):
    current_term = meta['terms'][-1]['name']

    query = {'roles': {'$elemMatch':
                       {'type': 'member',
                        'level': meta['level'],
                        meta['level']: meta['abbreviation'],
                        'term': current_term},
                      },
             'votesmart_id': None,
            }

    updated = 0
    initial_count = db.legislators.find(query).count()

    # get officials
    abbrev = meta['_id'].upper()

    if meta['level'] == 'state':
        upper_officials = votesmart.officials.getByOfficeState(9, abbrev)
        try:
            lower_officials = votesmart.officials.getByOfficeState(8, abbrev)
        except VotesmartApiError:
            lower_officials = votesmart.officials.getByOfficeState(7, abbrev)
    elif meta['level'] == 'country':
        lower_officials = votesmart.officials.getByOfficeState(5, abbrev)
        upper_officials = votesmart.officials.getByOfficeState(6, abbrev)

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


def update_transparencydata_legislators(meta, sunlight_key):
    current_term = meta['terms'][-1]['name']
    query = {'roles': {'$elemMatch':
                       {'type': 'member',
                        'level': meta['level'],
                        meta['level']: meta['abbreviation'],
                        'term': current_term},
                      },
             'transparencydata_id': None,
             'active': True,
            }

    updated = 0
    initial_count = db.legislators.find(query).count()
    abbrev = meta['_id'].upper()

    for leg in db.legislators.find(query):
        query = urllib.urlencode({'apikey': sunlight_key,
                                  'search': leg['full_name'].encode('utf8')})
        url = 'http://transparencydata.com/api/1.0/entities.json?' + query
        data = urllib2.urlopen(url).read()
        results = json.loads(data)
        matches = []
        for result in results:
            if (result['state'] == abbrev and
                result['seat'][6:] == leg['chamber'] and
                result['type'] == 'politician'):
                matches.append(result)

        if len(matches) == 1:
            leg['transparencydata_id'] = matches[0]['id']
            db.legislators.save(leg, safe=True)
            updated += 1

    print 'Updated %s of %s missing transparencydata ids' % (updated,
                                                             initial_count)


def update_missing_ids(abbr, sunlight_key):
    meta = db.metadata.find_one({'_id': abbr.lower()})
    if not meta:
        print "'{0}' does not exist in the database.".format(abbr)
        sys.exit(1)
    else:
        print "Updating ids for {0}".format(abbr)

    print "Updating PVS legislator ids..."
    update_votesmart_legislators(meta)

    print "Updating TransparencyData ids..."
    update_transparencydata_legislators(meta, sunlight_key)


def main():
    parser = argparse.ArgumentParser(
        description=('attempt to match legislators with ids in other'
                     'relevant APIs'),
        parents=[base_arg_parser],
    )

    parser.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                        help='abbreviations for data to update')

    args = parser.parse_args()

    settings.update(args)

    votesmart.apikey = settings.VOTESMART_API_KEY

    for abbr in args.abbrs:
        update_missing_ids(abbr, settings.SUNLIGHT_SERVICES_KEY)
        time.sleep(30)


if __name__ == '__main__':
    main()
