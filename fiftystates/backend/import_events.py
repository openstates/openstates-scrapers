#!/usr/bin/env python
import os
import sys
import glob
import logging
import datetime

try:
    import json
except:
    import simplejson as json

from fiftystates import settings
from fiftystates.backend import db
from fiftystates.backend.names import get_legislator_id
from fiftystates.backend.utils import (base_arg_parser, prepare_obj,
                                       update, get_committee_id)

import pymongo
from pymongo.son import SON
import argparse


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


def import_events(state, data_dir):
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

    ensure_indexes()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        parents=[base_arg_parser],
        description='Import scraped events.')

    parser.add_argument('--data_dir', '-d', type=str,
                        help='the base Fifty State data directory')

    args = parser.parse_args()

    if args.data_dir:
        data_dir = args.data_dir
    else:
        data_dir = settings.FIFTYSTATES_DATA_DIR

    import_events(args.state, data_dir)
