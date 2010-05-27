#!/usr/bin/env python
from __future__ import with_statement
import os

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates.backend import db

import argparse


def import_metadata(state, data_dir):
    data_dir = os.path.join(data_dir, state)
    with open(os.path.join(data_dir, 'state_metadata.json')) as f:
        data = json.load(f)

    data['_id'] = state
    db.metadata.save(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=('Import scraped state metadata into a mongo database.'))

    parser.add_argument('state', type=str,
                        help=('the two-letter abbreviation of the state to '
                              'import'))
    parser.add_argument('--data_dir', '-d', type=str,
                        help='the base Fifty State data directory')

    args = parser.parse_args()

    if not args.data_dir:
        args.data_dir = os.path.join(os.path.abspath(os.path.dirname(
                    __file__)), '..', '..', 'data')

    import_metadata(args.state, args.data_dir)
