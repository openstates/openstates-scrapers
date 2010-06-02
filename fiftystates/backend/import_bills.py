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
from fiftystates.backend.utils import (insert_with_id, keywordize,
                                       update, prepare_obj, base_arg_parser)

import pymongo
import argparse


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

        if not bill:
            data['created_at'] = datetime.datetime.now()
            data['updated_at'] = data['created_at']
            data['keywords'] = list(keywordize(data['title']))
            insert_with_id(data)
        else:
            data['keywords'] = list(keywordize(data['title']))
            update(bill, data, db.bills)


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
