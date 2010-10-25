#!/usr/bin/env python
from __future__ import with_statement
import os
import sys
import glob
import datetime

try:
    import json
except:
    import simplejson as json

from fiftystates.backend import db
from fiftystates.backend.utils import insert_with_id, update, prepare_obj

import pymongo
import name_tools


def ensure_indexes():
    db.legislators.ensure_index('_all_ids', pymongo.ASCENDING)
    db.legislators.ensure_index([('roles.state', pymongo.ASCENDING),
                                 ('roles.type', pymongo.ASCENDING),
                                 ('roles.term', pymongo.ASCENDING),
                                 ('roles.chamber', pymongo.ASCENDING),
                                 ('full_name', pymongo.ASCENDING),
                                 ('first_name', pymongo.ASCENDING),
                                 ('last_name', pymongo.ASCENDING),
                                 ('middle_name', pymongo.ASCENDING),
                                 ('suffixes', pymongo.ASCENDING)],
                                name='role_and_name_parts')


def import_legislators(state, data_dir):
    data_dir = os.path.join(data_dir, state)
    pattern = os.path.join(data_dir, 'legislators', '*.json')
    paths = glob.glob(pattern)
    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        import_legislator(data)

    print 'imported %s legislator files' % len(paths)
    activate_legislators(state)


def activate_legislators(state):
    """
    Sets the 'active' flag on legislators and populates top-level
    district/chamber/party fields for currently serving legislators.
    """
    meta = db.metadata.find_one({'_id': state})
    current_term = meta['terms'][-1]['name']

    for legislator in db.legislators.find({'roles': {'$elemMatch':
                                                     {'state': state,
                                                      'type': 'member'}}}):
        active_role = legislator['roles'][0]

        if active_role['term'] == current_term and not active_role['end_date']:
            legislator['active'] = True
            legislator['party'] = active_role['party']
            legislator['district'] = active_role['district']
            legislator['chamber'] = active_role['chamber']
        else:
            legislator['active'] = False
            for key in ('district', 'chamber', 'party'):
                try:
                    del legislator[key]
                except KeyError:
                    pass

        db.legislators.save(legislator, safe=True)


def import_legislator(data):
    # Rename 'role' -> 'type'
    for role in data['roles']:
        if 'role' in role:
            role['type'] = role['role']
            del role['role']

    cur_role = data['roles'][0]

    spec = {'state': data['state'],
            'term': cur_role['term'],
            'type': cur_role['type']}
    if 'district' in cur_role:
        spec['district'] = cur_role['district']
    if 'chamber' in cur_role:
        spec['chamber'] = cur_role['chamber']

    leg = db.legislators.find_one(
        {'state': data['state'],
         'full_name': data['full_name'],
         'roles': {'$elemMatch': spec}})

    if not leg:
        metadata = db.metadata.find_one({'_id': data['state']})

        term_names = [t['name'] for t in metadata['terms']]

        try:
            index = term_names.index(cur_role['term'])

            if index > 0:
                prev_term = term_names[index - 1]
                spec['term'] = prev_term
                prev_leg = db.legislators.find_one(
                    {'full_name': data['full_name'],
                     'roles': {'$elemMatch': spec}})

                if prev_leg:
                    update(prev_leg, data, db.legislators)
                    return
        except ValueError:
            print "Invalid term: %s" % cur_role['term']
            sys.exit(1)

        data['created_at'] = datetime.datetime.utcnow()
        data['updated_at'] = datetime.datetime.utcnow()

        insert_with_id(data)
    else:
        update(leg, data, db.legislators)

    ensure_indexes()
