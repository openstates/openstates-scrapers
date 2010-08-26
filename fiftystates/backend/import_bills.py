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

from fiftystates import settings
from fiftystates.backend import db
from fiftystates.backend.names import get_legislator_id
from fiftystates.backend.utils import (insert_with_id, keywordize,
                                       update, prepare_obj, base_arg_parser)

import pymongo
import argparse


def ensure_indexes():
    db.bills.ensure_index([('state', pymongo.ASCENDING),
                           ('session', pymongo.ASCENDING),
                           ('chamber', pymongo.ASCENDING),
                           ('bill_id', pymongo.ASCENDING)])
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
    for path in glob.iglob(pattern):
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
            for vtype in ('yes_votes', 'no_votes', 'other_votes'):
                svlist = []
                for svote in vote[vtype]:
                    id = get_legislator_id(state, data['session'],
                                           vote['chamber'], svote)
                    svlist.append({'name': svote, 'leg_id': id})

                vote[vtype] = svlist

        if not bill:
            data['created_at'] = datetime.datetime.now()
            data['updated_at'] = data['created_at']
            data['_keywords'] = list(keywordize(data['title']))
            insert_with_id(data)
        else:
            data['_keywords'] = list(keywordize(data['title']))
            update(bill, data, db.bills)

    ensure_indexes()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        parents=[base_arg_parser],
        description='Import scraped state legislation into a mongo databse.')

    parser.add_argument('--data_dir', '-d', type=str,
                        help='the base Fifty State data directory')

    args = parser.parse_args()

    if args.data_dir:
        data_dir = args.data_dir
    else:
        data_dir = settings.FIFTYSTATES_DATA_DIR

    import_bills(args.state, data_dir)
