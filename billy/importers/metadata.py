#!/usr/bin/env python
import os
import datetime
import json

from billy import db
from billy.importers.utils import prepare_obj

PRESERVED_FIELDS = ('latest_dump_url', 'latest_dump_date',
                    'latest_csv_url', 'latest_csv_date')


def import_metadata(state, data_dir):
    preserved = {}
    old_metadata = db.metadata.find_one({'_id': state}) or {}
    for field in PRESERVED_FIELDS:
        if field in old_metadata:
            preserved[field] = old_metadata[field]

    data_dir = os.path.join(data_dir, state)
    with open(os.path.join(data_dir, 'state_metadata.json')) as f:
        data = json.load(f)
        data['_type'] = 'metadata'
        data = prepare_obj(data)

    data['_id'] = state
    data.update(preserved)

    data['latest_update'] = datetime.datetime.utcnow()

    db.metadata.save(data, safe=True)
