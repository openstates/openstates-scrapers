#!/usr/bin/env python
from __future__ import with_statement
import os
import glob
import logging
import datetime

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates import settings
from fiftystates.backend import db
from fiftystates.backend.names import get_legislator_id
from fiftystates.backend.utils import base_arg_parser, prepare_obj

import argparse

_log = logging.getLogger('fiftystates')


def import_votes(state, data_dir):
    data_dir = os.path.join(data_dir, state)
    pattern = os.path.join(data_dir, 'votes', '*.json')
    for path in glob.iglob(pattern):
        with open(path) as f:
            data = prepare_obj(json.load(f))

        bill = db.bills.find_one({'state': state,
                                  'chamber': data['bill_chamber'],
                                  'session': data['session'],
                                  'bill_id': data['bill_id']})

        if not bill:
            _log.warning("Couldn't find bill %s" % data['bill_id'])
            continue

        del data['bill_id']
        del data['filename']

        for vtype in ('yes_votes', 'no_votes', 'other_votes'):
            svlist = []
            for svote in data[vtype]:
                id = get_legislator_id(state, data['session'],
                                       data['chamber'], svote)
                svlist.append({'name': svote, 'leg_id': id})

            data[vtype] = svlist

        for vote in bill['votes']:
            if (vote['motion'] == data['motion']
                and vote['date'] == data['date']):
                vote.update(data)
        else:
            bill['votes'].append(data)

        db.bills.save(bill)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        parents=[base_arg_parser],
        description=("Import (separate file) votes from scraped "
                     "legislative data."))

    parser.add_argument('--data_dir', '-d', type=str,
                        help="the base Fifty State data directory")

    args = parser.parse_args()

    if args.data_dir:
        data_dir = args.data_dir
    else:
        data_dir = settings.FIFTYSTATES_DATA_DIR

    _log.addHandler(logging.StreamHandler())

    import_votes(args.state, data_dir)
