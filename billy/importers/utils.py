import os
import re
import time
import json
import logging
import datetime
from collections import defaultdict

from pymongo.son import SON
import pymongo.errors

from billy import db

import name_tools


def _get_property_dict(schema):
    """ given a schema object produce a nested dictionary of fields """
    pdict = {}
    for k, v in schema['properties'].iteritems():
        pdict[k] = {}
        if 'items' in v and 'properties' in v['items']:
            pdict[k] = _get_property_dict(v['items'])
    return pdict

# load standard fields from schema files
standard_fields = {}
for _type in ('bill', 'person', 'committee', 'metadata', 'vote', 'event'):
    fname = os.path.join(os.path.split(__file__)[0],
                         '../schemas/%s.json' % _type)
    schema = json.load(open(fname))
    standard_fields[_type] = _get_property_dict(schema)


def insert_with_id(obj):
    """
    Generates a unique ID for the supplied legislator/committee/bill
    and inserts it into the appropriate collection.
    """
    if '_id' in obj:
        raise ValueError("object already has '_id' field")

    # add created_at/updated_at on insert
    obj['created_at'] = datetime.datetime.utcnow()
    obj['updated_at'] = obj['created_at']

    if obj['_type'] == 'person' or obj['_type'] == 'legislator':
        collection = db.legislators
        id_type = 'L'
    elif obj['_type'] == 'committee':
        collection = db.committees
        id_type = 'C'
    elif obj['_type'] == 'bill':
        collection = db.bills
        id_type = 'B'
    else:
        raise ValueError("unknown _type for object")

    level = obj[obj['level']].upper()

    id_reg = re.compile('^%s%s' % (level, id_type))

    # Find the next available _id and insert
    id_prefix = '%s%s' % (level, id_type)
    cursor = collection.find({'_id': id_reg}).sort('_id', -1).limit(1)

    try:
        new_id = int(cursor.next()['_id'][3:]) + 1
    except StopIteration:
        new_id = 1

    while True:
        obj['_id'] = '%s%06d' % (id_prefix, new_id)
        obj['_all_ids'] = [obj['_id']]

        if obj['_type'] in ['person', 'legislator']:
            obj['leg_id'] = obj['_id']

        try:
            return collection.insert(obj, safe=True)
        except pymongo.errors.DuplicateKeyError:
            new_id += 1


def _timestamp_to_dt(timestamp):
    tstruct = time.localtime(timestamp)
    dt = datetime.datetime(*tstruct[0:6])
    if tstruct.tm_isdst:
        dt = dt - datetime.timedelta(hours=1)
    return dt


def update(old, new, coll):
    # To prevent deleting standalone votes..
    if 'votes' in new and not new['votes']:
        del new['votes']

    # need_save = something has changed
    need_save = False

    locked_fields = old.get('_locked_fields', [])

    for key, value in new.items():

        # don't update locked fields
        if key in locked_fields:
            continue

        if old.get(key) != value:
            old[key] = value
            need_save = True

        # remove old +key field if this field no longer has a +
        plus_key = '+%s' % key
        if plus_key in old:
            del old[plus_key]
            need_save = True

    if need_save:
        old['updated_at'] = datetime.datetime.utcnow()
        coll.save(old, safe=True)


def convert_timestamps(obj):
    """
    Convert unix timestamps in the scraper output to python datetimes
    so that they will be saved properly as Mongo datetimes.
    """
    for key in ('date', 'when', 'end', 'start_date', 'end_date'):
        value = obj.get(key)
        if value:
            try:
                obj[key] = _timestamp_to_dt(value)
            except TypeError:
                raise TypeError("expected float for %s, got %s" % (key, value))

    for key in ('sources', 'actions', 'votes'):
        for child in obj.get(key, []):
            convert_timestamps(child)

    for term in obj.get('terms', []):
        convert_timestamps(term)

    for details in obj.get('session_details', {}).values():
        convert_timestamps(details)

    for role in obj.get('roles', []):
        convert_timestamps(role)

    return obj


def split_name(obj):
    """
    If the supplied legislator/person object is missing 'first_name'
    or 'last_name' then use name_tools to split.
    """
    if obj['_type'] in ('person', 'legislator'):
        for key in ('first_name', 'last_name'):
            if key not in obj or not obj[key]:
                # Need to split
                (obj['first_name'], obj['last_name'],
                 obj['suffixes']) = name_tools.split(obj['full_name'])[1:]
                break

    return obj


def _make_plus_helper(obj, fields):
    """ add a + prefix to any fields in obj that aren't in fields """
    new_obj = {}

    for key, value in obj.iteritems():
        if key in fields or key.startswith('_'):
            # if there's a subschema apply it to a list or subdict
            if fields.get(key):
                if isinstance(value, list):
                    value = [_make_plus_helper(item, fields[key])
                             for item in value]
            # assign the value (modified potentially) to the new_obj
            new_obj[key] = value
        else:
            # values not in the fields dict get a +
            new_obj['+%s' % key] = value

    return new_obj


def make_plus_fields(obj):
    """
    Add a '+' to the key of non-standard fields.

    dispatch to recursive _make_plus_helper based on _type field
    """
    fields = standard_fields.get(obj['_type'], dict())
    return _make_plus_helper(obj, fields)


def prepare_obj(obj):
    """
    Clean up scraped objects in preparation for MongoDB.
    """
    convert_timestamps(obj)

    if obj['_type'] in ('person', 'legislator'):
        split_name(obj)

    return make_plus_fields(obj)


def merge_legislators(old, new):
    all_ids = set(old['_all_ids']).union(new['_all_ids'])
    new['_all_ids'] = list(all_ids)
    db.legislators.remove({'_id': new['_id']})
    new['_id'] = old['_id']
    new['leg_id'] = new['_id']
    db.legislators.save(new, safe=True)


def next_big_id(abbr, letter, collection):
    query = SON([('_id', abbr)])
    update = SON([('$inc', SON([('seq', 1)]))])
    seq = db.command(SON([('findandmodify', collection),
                          ('query', query),
                          ('update', update),
                          ('new', True),
                          ('upsert', True)]))['value']['seq']
    return "%s%s%08d" % (abbr.upper(), letter, seq)

