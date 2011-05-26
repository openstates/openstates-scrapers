#!/usr/bin/env python
import os
import glob
import datetime
import json

from billy import db
from billy.importers.utils import insert_with_id, update, prepare_obj

import pymongo


def ensure_indexes():
    db.legislators.ensure_index('_all_ids', pymongo.ASCENDING)
    db.legislators.ensure_index([('roles.state', pymongo.ASCENDING),
                                 ('roles.type', pymongo.ASCENDING),
                                 ('roles.term', pymongo.ASCENDING),
                                 ('roles.chamber', pymongo.ASCENDING),
                                 ('_scraped_name', pymongo.ASCENDING),
                                 ('first_name', pymongo.ASCENDING),
                                 ('last_name', pymongo.ASCENDING),
                                 ('middle_name', pymongo.ASCENDING),
                                 ('suffixes', pymongo.ASCENDING)],
                                name='role_and_name_parts')


def import_legislators(abbr, data_dir):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'legislators', '*.json')
    paths = glob.glob(pattern)
    for path in paths:
        with open(path) as f:
            import_legislator(json.load(f))

    print 'imported %s legislator files' % len(paths)

    meta = db.metadata.find_one({'_id': abbr})
    current_term = meta['terms'][-1]['name']
    level = meta['level']

    activate_legislators(current_term, abbr, level)
    deactivate_legislators(current_term, abbr, level)

    ensure_indexes()


def activate_legislators(current_term, abbr, level):
    """
    Sets the 'active' flag on legislators and populates top-level
    district/chamber/party fields for currently serving legislators.
    """
    # to support multiple levels we adopt the pattern of
    # 'level': level,  level: abbr
    # this means that level must always be a key name that maps to the abbr

    for legislator in db.legislators.find({'roles': {'$elemMatch':
                                                     {'level': level,
                                                      level: abbr,
                                                      'type': 'member',
                                                      'term': current_term}}}):
        active_role = legislator['roles'][0]

        if not active_role['end_date']:
            legislator['active'] = True
            legislator['party'] = active_role['party']
            legislator['district'] = active_role['district']
            legislator['chamber'] = active_role['chamber']

        legislator['updated_at'] = datetime.datetime.utcnow()
        db.legislators.save(legislator, safe=True)


def deactivate_legislators(current_term, abbr, level):

    # legislators without a current term role or with an end_date
    for leg in db.legislators.find(
        {'$or': [
            {'roles': {'$elemMatch':
                       {'term': {'$ne': current_term},
                        'type': 'member',
                         'level': level,
                          level: abbr,
                       }},
            },
            {'roles': {'$elemMatch':
                       {'term': current_term,
                        'type': 'member',
                         'level': level,
                          level: abbr,
                        'end_date': {'$ne':None}}},
            },

        ]}):

        if 'old_roles' not in leg:
            leg['old_roles'] = {}

        leg['old_roles'][leg['roles'][0]['term']] = leg['roles']
        leg['roles'] = []
        leg['active'] = False

        for key in ('district', 'chamber', 'party'):
            if key in leg:
                del leg[key]

        leg['updated_at'] = datetime.datetime.utcnow()
        db.legislators.save(leg, safe=True)


def get_previous_term(abbrev, term):
    meta = db.metadata.find_one({'_id': abbrev})
    t1 = meta['terms'][0]
    for t2 in meta['terms'][1:]:
        if t2['name'] == term:
            return t1['name']
        t1 = t2

    return None


def get_next_term(abbrev, term):
    meta = db.metadata.find_one({'_id': abbrev})
    t1 = meta['terms'][0]
    for t2 in meta['terms'][1:]:
        if t1['name'] == term:
            return t2['name']
        t1 = t2

    return None


def import_legislator(data):
    data = prepare_obj(data)
    data['_scraped_name'] = data['full_name']

    # Rename 'role' -> 'type'
    for role in data['roles']:
        if 'role' in role:
            role['type'] = role['role']
            del role['role']

        # copy over country and/or state into role
        # TODO: base this on all possible level fields
        role['level'] = data['level']
        if 'country' in data:
            role['country'] = data['country']
        if 'state' in data:
            role['state'] = data['state']

    cur_role = data['roles'][0]
    term = cur_role['term']

    level = data['level']
    abbrev = data[level]

    prev_term = get_previous_term(abbrev, term)
    next_term = get_next_term(abbrev, term)

    spec = {level: abbrev,
            'type': cur_role['type'],
            'term': {'$in': [term, prev_term, next_term]}}
    if 'district' in cur_role:
        spec['district'] = cur_role['district']
    if 'chamber' in cur_role:
        spec['chamber'] = cur_role['chamber']

    leg = db.legislators.find_one(
        {'level': level, level: abbrev,
         '_scraped_name': data['full_name'],
         'roles': {'$elemMatch': spec}})

    if leg:
        if 'old_roles' not in leg:
            leg['old_roles'] = {}

        if leg['roles'][0]['term'] == prev_term:
            # Move to old
            leg['old_roles'][leg['roles'][0]['term']] = leg['roles']
        elif leg['roles'][0]['term'] == next_term:
            leg['old_roles'][term] = data['roles']
            data['roles'] = leg['roles']

        update(leg, data, db.legislators)
    else:
        insert_with_id(data)
