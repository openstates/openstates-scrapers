#!/usr/bin/env python
from __future__ import with_statement
import os

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates.backend import db
from fiftystates.backend.utils import prepare_obj


def import_metadata(state, data_dir):
    data_dir = os.path.join(data_dir, state)
    with open(os.path.join(data_dir, 'state_metadata.json')) as f:
        data = json.load(f)
        data['_type'] = 'metadata'
        data = prepare_obj(data)

    data['_id'] = state
    db.metadata.save(data, safe=True)
