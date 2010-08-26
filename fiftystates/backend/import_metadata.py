#!/usr/bin/env python
from __future__ import with_statement
import os

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates import settings
from fiftystates.backend import db
from fiftystates.backend.utils import base_arg_parser, prepare_obj

import argparse


def import_metadata(state, data_dir):
    data_dir = os.path.join(data_dir, state)
    with open(os.path.join(data_dir, 'state_metadata.json')) as f:
        data = json.load(f)
        data['_type'] = 'metadata'
        data = prepare_obj(data)

    data['_id'] = state
    db.metadata.save(data, safe=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        parents=[base_arg_parser],
        description=('Import scraped state metadata into a mongo database.'))

    parser.add_argument('--data_dir', '-d', type=str,
                        help='the base Fifty State data directory')

    args = parser.parse_args()

    if args.data_dir:
        data_dir = args.data_dir
    else:
        data_dir = settings.FIFTYSTATES_DATA_DIR

    import_metadata(args.state, data_dir)
