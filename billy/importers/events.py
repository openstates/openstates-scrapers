#!/usr/bin/env python
import os
import glob
import logging
import datetime
import json

from billy import db
from billy.importers.utils import prepare_obj, update, next_big_id
from billy.scrape.events import Event

import pymongo

def ensure_indexes():
    db.events.ensure_index([('when', pymongo.ASCENDING),
                            ('state', pymongo.ASCENDING),
                            ('type', pymongo.ASCENDING)])
    db.events.ensure_index([('when', pymongo.DESCENDING),
                            ('state', pymongo.ASCENDING),
                            ('type', pymongo.ASCENDING)])


def _insert_with_id(event):
    abbr = event[event['level']]
    id = next_big_id(abbr, 'E', 'event_ids')
    logging.info("Saving as %s" % id)

    event['_id'] = id
    db.events.save(event, safe=True)

    return id


def import_events(abbr, data_dir, import_actions=False):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'events', '*.json')

    for path in glob.iglob(pattern):
        with open(path) as f:
            data = prepare_obj(json.load(f))

            import_event(data)

    ensure_indexes()

def import_event(data):
    event = None
    level = data['level']

    if '_guid' in data:
        event = db.events.find_one({'level': level,
                                    level: data[level],
                                    '_guid': data['_guid']})

    if not event:
        event = db.events.find_one({'level': level,
                                    level: data[level],
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

# IMPORTANT: if/when actions_to_events is re-enabled it definitely
# needs to be updated to support level
#    if import_actions:
#        actions_to_events(state)

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
