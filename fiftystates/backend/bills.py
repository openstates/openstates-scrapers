#!/usr/bin/env python
from __future__ import with_statement
import os
import re
import sys
import time
import glob
import datetime

try:
    import json
except:
    import simplejson as json

from fiftystates.utils import keywordize
from fiftystates.backend import db
from fiftystates.backend.names import get_legislator_id
from fiftystates.backend.utils import (insert_with_id,
                                       update, prepare_obj,
                                       get_committee_id)

import pymongo


def ensure_indexes():
    db.bills.ensure_index([('state', pymongo.ASCENDING),
                           ('session', pymongo.ASCENDING),
                           ('chamber', pymongo.ASCENDING),
                           ('bill_id', pymongo.ASCENDING)])
    db.bills.ensure_index([('state', pymongo.ASCENDING),
                           ('_current_term', pymongo.ASCENDING),
                           ('_current_session', pymongo.ASCENDING),
                           ('chamber', pymongo.ASCENDING),
                           ('keywords', pymongo.ASCENDING)])
    db.bills.ensure_index([('state', pymongo.ASCENDING),
                           ('session', pymongo.ASCENDING),
                           ('chamber', pymongo.ASCENDING),
                           ('_keywords', pymongo.ASCENDING)])
    db.bills.ensure_index([('state', pymongo.ASCENDING),
                           ('session', pymongo.ASCENDING),
                           ('chamber', pymongo.ASCENDING),
                           ('type', pymongo.ASCENDING)])
    db.bills.ensure_index([('state', pymongo.ASCENDING),
                           ('session', pymongo.ASCENDING),
                           ('chamber', pymongo.ASCENDING),
                           ('sponsors', pymongo.ASCENDING)])


def import_bills(state, data_dir):
    data_dir = os.path.join(data_dir, state)
    pattern = os.path.join(data_dir, 'bills', '*.json')

    meta = db.metadata.find_one({'_id': state})

    # Build a session to term mapping
    sessions = {}
    for term in meta['terms']:
        for session in term['sessions']:
            sessions[session] = term['name']

    paths = glob.glob(pattern)

    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        bill = db.bills.find_one({'state': data['state'],
                                  'session': data['session'],
                                  'chamber': data['chamber'],
                                  'bill_id': data['bill_id']})

        for sponsor in data['sponsors']:
            id = get_legislator_id(state, data['session'], None,
                                   sponsor['name'])
            sponsor['leg_id'] = id

        for vote in data['votes']:
            if 'committee' in vote:
                committee_id = get_committee_id(state,
                                                vote['chamber'],
                                                vote['committee'])
                vote['committee_id'] = committee_id

            for vtype in ('yes_votes', 'no_votes', 'other_votes'):
                svlist = []
                for svote in vote[vtype]:
                    id = get_legislator_id(state, data['session'],
                                           vote['chamber'], svote)
                    svlist.append({'name': svote, 'leg_id': id})

                vote[vtype] = svlist

        data['_term'] = sessions[data['session']]

        # Merge any version titles into the alternate_titles list
        alt_titles = set(data.get('alternate_titles', []))
        for version in data['versions']:
            if 'title' in version:
                alt_titles.add(version['title'])
            if '+short_title' in version:
                alt_titles.add(version['+short_title'])
        try:
            # Make sure the primary title isn't included in the
            # alternate title list
            alt_titles.remove(data['title'])
        except KeyError:
            pass
        data['alternate_titles'] = list(alt_titles)

        if not bill:
            data['created_at'] = datetime.datetime.utcnow()
            data['updated_at'] = data['created_at']
            data['_keywords'] = list(bill_keywords(data))
            insert_with_id(data)
        else:
            data['_keywords'] = list(bill_keywords(data))
            update(bill, data, db.bills)

    print 'imported %s bill files' % len(paths)

    populate_current_fields(state)
    ensure_indexes()


def bill_keywords(bill):
    """
    Get the keyword set for all of a bill's titles.
    """
    keywords = keywordize(bill['title'])
    for title in bill['alternate_titles']:
        keywords = keywords.union(keywordize(title))
    return keywords


def populate_current_fields(state):
    """
    Set/update _current_term and _current_session fields on all bills
    from the given state.
    """
    meta = db.metadata.find_one({'_id': state})
    current_term = meta['terms'][-1]
    current_session = current_term['sessions'][-1]

    for bill in db.bills.find({'state': state}):
        if bill['session'] == current_session:
            bill['_current_session'] = True
        else:
            bill['_current_session'] = False

        if bill['session'] in current_term['sessions']:
            bill['_current_term'] = True
        else:
            bill['_current_term'] = False

        db.bills.save(bill, safe=True)
