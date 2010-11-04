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
from fiftystates.backend.utils import prepare_obj, update, insert_with_id

import pymongo
import name_tools


def ensure_indexes():
    db.committees.ensure_index([('state', pymongo.ASCENDING),
                                ('committee', pymongo.ASCENDING),
                                ('subcommittee', pymongo.ASCENDING)])


def import_committees(state, data_dir):
    data_dir = os.path.join(data_dir, state)
    pattern = os.path.join(data_dir, 'committees', '*.json')

    meta = db.metadata.find_one({'_id': state})
    current_term = meta['terms'][-1]['name']

    paths = glob.glob(pattern)

    if not paths:
        # Not standalone committees
        for legislator in db.legislators.find({
            'roles': {'$elemMatch': {'term': current_term,
                                     'state': state}}}):

            for role in legislator['roles']:
                if (role['type'] == 'committee member' and
                    'committee_id' not in role):

                    spec = {'state': role['state'],
                            'chamber': role['chamber'],
                            'committee': role['committee']}
                    if 'subcommittee' in role:
                        spec['subcommittee'] = role['subcommittee']

                    committee = db.committees.find_one(spec)

                    if not committee:
                        committee = spec
                        committee['_type'] = 'committee'
                        committee['members'] = []
                        committee['sources'] = []
                        insert_with_id(committee)

                    for member in committee['members']:
                        if member['leg_id'] == legislator['leg_id']:
                            break
                    else:
                        committee['members'].append(
                            {'name': legislator['full_name'],
                             'leg_id': legislator['leg_id'],
                             'role': 'member'})
                        db.committees.save(committee, safe=True)

                        role['committee_id'] = committee['_id']

            db.legislators.save(legislator, safe=True)

    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        spec = {'state': state,
                'chamber': data['chamber'],
                'committee': data['committee']}
        if 'subcommittee' in data:
            spec['subcommittee'] = data['subcommittee']

        committee = db.committees.find_one(spec)

        if not committee:
            insert_with_id(data)
            committee = data
        else:
            update(committee, data, db.committees)

        for member in committee['members']:
            if not member['name']:
                continue

            (pre, first, last, suff) = name_tools.split(member['name'])

            found = db.legislators.find({
                    'first_name': first,
                    'last_name': last,
                    'roles': {'$elemMatch': {'term': current_term,
                                             'state': state}}})

            if found.count() > 1:
                print "Too many matches for %s" % member['name'].encode(
                    'ascii', 'ignore')
                member['leg_id'] = None
                continue
            elif found.count() == 0:
                print "No matches for %s" % member['name'].encode(
                    'ascii', 'ignore')
                member['leg_id'] = None
                continue

            legislator = found[0]

            member['leg_id'] = legislator['_id']

            for role in legislator['roles']:
                if (role['type'] == 'committee member' and
                    role['term'] == current_term and
                    role['committee_id'] == committee['_id']):
                    break
            else:
                new_role = {'type': 'committee member',
                            'committee': committee['committee'],
                            'term': current_term,
                            'chamber': committee['chamber'],
                            'committee_id': committee['_id'],
                            'state': state}
                if 'subcommittee' in committee:
                    new_role['subcommittee'] = committee['subcommittee']
                legislator['roles'].append(new_role)
                legislator['updated_at'] = datetime.datetime.utcnow()
                db.legislators.save(legislator, safe=True)

        db.committees.save(committee, safe=True)

    print 'imported %s committee files' % len(paths)

    link_parents(state)

    ensure_indexes()


def link_parents(state):
    for comm in db.committees.find({'state': state}):
        sub = comm.get('subcommittee')
        if not sub:
            comm['parent_id'] = None
        else:
            parent = db.committees.find_one({'state': state,
                                             'chamber': comm['chamber'],
                                             'committee': comm['committee']})
            if not parent:
                print "Failed finding parent for: %s" % sub
                comm['parent_id'] = None
            else:
                comm['parent_id'] = parent['_id']

        db.committees.save(comm)
