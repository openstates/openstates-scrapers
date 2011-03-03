#!/usr/bin/env python
from __future__ import with_statement
import os
import re
import sys
import time
import glob
import datetime
from collections import defaultdict

try:
    import json
except:
    import simplejson as json

from billy.utils import keywordize
from billy import db
from billy.importers.names import get_legislator_id
from billy.importers.utils import (insert_with_id,
                                   update, prepare_obj,
                                   get_committee_id,
                                   fix_bill_id,
                                   VoteMatcher,)

import pymongo


def ensure_indexes():
    db.bills.ensure_index([('state', pymongo.ASCENDING),
                           ('session', pymongo.ASCENDING),
                           ('chamber', pymongo.ASCENDING),
                           ('bill_id', pymongo.ASCENDING)],
                          unique=True)
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
                           ('subjects', pymongo.ASCENDING)])
    db.bills.ensure_index([('state', pymongo.ASCENDING),
                           ('session', pymongo.ASCENDING),
                           ('chamber', pymongo.ASCENDING),
                           ('sponsors', pymongo.ASCENDING)])

def import_votes(state, data_dir):
    pattern = os.path.join(data_dir, 'votes', '*.json')
    paths = glob.glob(pattern)

    votes = defaultdict(list)

    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        # need to match bill_id already in the database
        bill_id = fix_bill_id(data.pop('bill_id'))

        votes[(data['bill_chamber'], data['session'], bill_id)].append(data)

    print 'imported %s vote files' % len(paths)
    return votes


def import_bills(state, data_dir):
    data_dir = os.path.join(data_dir, state)
    pattern = os.path.join(data_dir, 'bills', '*.json')

    meta = db.metadata.find_one({'_id': state})

    # Build a session to term mapping
    sessions = {}
    for term in meta['terms']:
        for session in term['sessions']:
            sessions[session] = term['name']

    votes = import_votes(state, data_dir)

    paths = glob.glob(pattern)

    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        # clean up bill_id
        data['bill_id'] = fix_bill_id(data['bill_id'])

        # move subjects to scraped_subjects
        subjects = data.pop('subjects', None)
        if subjects:
            data['scraped_subjects'] = subjects

        # add loaded votes to data
        bill_votes = votes.pop((data['chamber'], data['session'],
                                data['bill_id']), [])
        data['votes'].extend(bill_votes)

        bill = db.bills.find_one({'state': data['state'],
                                  'session': data['session'],
                                  'chamber': data['chamber'],
                                  'bill_id': data['bill_id']})

        vote_matcher = VoteMatcher(data['state'])
        if bill:
            vote_matcher.learn_vote_ids(bill['votes'])
        vote_matcher.set_vote_ids(data['votes'])

        # match sponsor leg_ids
        for sponsor in data['sponsors']:
            id = get_legislator_id(state, data['session'], None,
                                   sponsor['name'])
            sponsor['leg_id'] = id

        for vote in data['votes']:

            # committee_ids
            if 'committee' in vote:
                committee_id = get_committee_id(state,
                                                vote['chamber'],
                                                vote['committee'])
                vote['committee_id'] = committee_id

            # vote leg_ids
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
            data['_keywords'] = list(bill_keywords(data))
            insert_with_id(data)
        else:
            data['_keywords'] = list(bill_keywords(data))
            update(bill, data, db.bills)

    print 'imported %s bill files' % len(paths)

    for remaining in votes.keys():
        print 'Failed to match vote %s %s %s' % remaining

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
