#!/usr/bin/env python
import os
import glob
import datetime
import json

from billy import db
from billy.conf import settings
from billy.importers.names import get_legislator_id
from billy.importers.utils import prepare_obj, update, insert_with_id

import pymongo


def ensure_indexes():
    db.committees.ensure_index([('_all_ids', pymongo.ASCENDING)])
    db.committees.ensure_index([('state', pymongo.ASCENDING),
                                ('committee', pymongo.ASCENDING),
                                ('subcommittee', pymongo.ASCENDING)])

def import_committees_from_legislators(current_term, level, abbr):
    """ create committees from legislators that have committee roles """

    # for all current legislators
    for legislator in db.legislators.find({
        'level': level,
        'roles': {'$elemMatch': {'term': current_term,
                                 level: abbr}}}):

        # for all committee roles
        for role in legislator['roles']:
            if (role['type'] == 'committee member' and
                'committee_id' not in role):

                spec = {'level': level,
                        level: abbr,
                        'chamber': role['chamber'],
                        'committee': role['committee']}
                if 'subcommittee' in role:
                    spec['subcommittee'] = role['subcommittee']

                committee = db.committees.find_one(spec)

                if not committee:
                    committee = spec
                    committee['_type'] = 'committee'
                    # copy required fields from legislator to committee
                    for f in settings.BILLY_LEVEL_FIELDS:
                        committee[f] = legislator[f]
                    committee['members'] = []
                    committee['sources'] = []
                    if 'subcommittee' not in committee:
                        committee['subcommittee'] = None
                    insert_with_id(committee)

                for member in committee['members']:
                    if member['leg_id'] == legislator['leg_id']:
                        break
                else:
                    committee['members'].append(
                        {'name': legislator['full_name'],
                         'leg_id': legislator['leg_id'],
                         'role': role.get('position') or 'member'})
                    db.committees.save(committee, safe=True)

                    role['committee_id'] = committee['_id']

        db.legislators.save(legislator, safe=True)


def import_committee(data, current_session, current_term):
    level = data['level']
    abbr = data[level]
    spec = {'level': level,
            level: abbr,
            'chamber': data['chamber'],
            'committee': data['committee']}
    if 'subcommittee' in data:
        spec['subcommittee'] = data['subcommittee']

    # insert/update the actual committee object
    committee = db.committees.find_one(spec)

    if not committee:
        insert_with_id(data)
        committee = data
    else:
        update(committee, data, db.committees)

    # deal with the members, add roles
    for member in committee['members']:
        if not member['name']:
            continue

        leg_id = get_legislator_id(abbr, current_session,
                                   data['chamber'],
                                   member['name'])

        if not leg_id:
            print "No matches for %s" % member['name'].encode(
                'ascii', 'ignore')
            member['leg_id'] = None
            continue

        legislator = db.legislators.find_one({'_id': leg_id})

        member['leg_id'] = leg_id

        for role in legislator['roles']:
            if (role['type'] == 'committee member' and
                role['term'] == current_term and
                role.get('committee_id') == committee['_id']):
                break
        else:
            new_role = {'type': 'committee member',
                        'committee': committee['committee'],
                        'term': current_term,
                        'chamber': committee['chamber'],
                        'committee_id': committee['_id'],
                        'level': level,
                       }
            # copy over all necessary fields from committee
            for f in settings.BILLY_LEVEL_FIELDS:
                new_role[f] = committee[f]

            if 'subcommittee' in committee:
                new_role['subcommittee'] = committee['subcommittee']
            legislator['roles'].append(new_role)
            legislator['updated_at'] = datetime.datetime.utcnow()
            db.legislators.save(legislator, safe=True)

    db.committees.save(committee, safe=True)


def import_committees(abbr, data_dir):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'committees', '*.json')

    meta = db.metadata.find_one({'_id': abbr})
    current_term = meta['terms'][-1]['name']
    current_session = meta['terms'][-1]['sessions'][-1]
    level = meta['level']

    paths = glob.glob(pattern)

    for committee in db.committees.find({'level': level, level: abbr}):
        committee['members'] = []
        db.committees.save(committee, safe=True)

    # import committees from legislator roles, no standalone committees scraped
    if not paths:
        import_committees_from_legislators(current_term, level, abbr)

    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        import_committee(data, current_session, current_term)

    print 'imported %s committee files' % len(paths)

    link_parents(level, abbr)

    ensure_indexes()


def link_parents(level, abbr):
    for comm in db.committees.find({'level': level, level: abbr}):
        sub = comm.get('subcommittee')
        if not sub:
            comm['parent_id'] = None
        else:
            parent = db.committees.find_one({'level': level,
                                             level: abbr,
                                             'chamber': comm['chamber'],
                                             'committee': comm['committee']})
            if not parent:
                print "Failed finding parent for: %s" % sub
                comm['parent_id'] = None
            else:
                comm['parent_id'] = parent['_id']

        db.committees.save(comm, safe=True)
