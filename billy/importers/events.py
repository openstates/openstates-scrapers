#!/usr/bin/env python
import os
import sys
import glob
import logging
import datetime
import json

from billy import db
from billy.importers.names import get_legislator_id
from billy.importers.utils import prepare_obj, update, get_committee_id
from billy.scrape.events import Event

import pymongo
from pymongo.son import SON


def ensure_indexes():
    db.events.ensure_index([('when', pymongo.ASCENDING),
                            ('state', pymongo.ASCENDING),
                            ('type', pymongo.ASCENDING)])
    db.events.ensure_index([('when', pymongo.DESCENDING),
                            ('state', pymongo.ASCENDING),
                            ('type', pymongo.ASCENDING)])


def _insert_with_id(event):
    query = SON([('_id', event['state'])])
    update = SON([('$inc', SON([('seq', 1)]))])
    seq = db.command(SON([('findandmodify', 'event_ids'),
                          ('query', query),
                          ('update', update),
                          ('new', True),
                          ('upsert', True)]))['value']['seq']

    id = "%sE%08d" % (event['state'].upper(), seq)
    logging.info("Saving as %s" % id)

    event['_id'] = id
    db.events.save(event, safe=True)

    return id


def import_events(state, data_dir, import_actions=True):
    data_dir = os.path.join(data_dir, state)
    pattern = os.path.join(data_dir, 'events', '*.json')

    for path in glob.iglob(pattern):
        with open(path) as f:
            data = prepare_obj(json.load(f))

        event = None
        if '_guid' in data:
            event = db.events.find_one({'state': data['state'],
                                        '_guid': data['_guid']})

        if not event:
            event = db.events.find_one({'state': data['state'],
                                        'when': data['when'],
                                        'end': data['end'],
                                        'type': data['type'],
                                        'description': data['description']})

        if not event:
            data['created_at'] = datetime.datetime.utcnow()
            data['updated_at'] = data['created_at']
            _insert_with_id(data)
        else:
            update(event, data, db.events)

#    if import_actions:
#        actions_to_events(state)

    ensure_indexes()


def actions_to_events(state):
    for bill in db.bills.find({'state': state}):
        print "Converting %s actions to events" % bill['_id']

        count = 1
        for action in bill['actions']:
            guid = "%s:action:%06d" % (bill['_id'], count)
            count += 1

            event = db.events.find_one({'state': state,
                                        '_guid': guid})

            description = "%s: %s" % (bill['bill_id'], action['action'])
            data = Event(bill['session'], action['date'],
                         'bill:action', description, location=action['actor'],
                         action_type=action['type'])
            data.add_participant('actor', action['actor'])
            data['_guid'] = guid
            data['state'] = state

            if not event:
                data['created_at'] = datetime.datetime.utcnow()
                data['updated_at'] = data['created_at']
                _insert_with_id(data)
            else:
                update(event, data, db.events)
