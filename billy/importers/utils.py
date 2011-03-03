import os
import re
import time
import json
import logging
import datetime
from collections import defaultdict

from pymongo.son import SON
import pymongo.errors

from billy import db, fs

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
    if hasattr(obj, '_id'):
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

    id_reg = re.compile('^%s%s' % (obj['state'].upper(), id_type))

    # Find the next available _id and insert
    id_prefix = '%s%s' % (obj['state'].upper(), id_type)
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


def timestamp_to_dt(timestamp):
    return datetime.datetime(*time.localtime(timestamp)[0:6])


def update(old, new, coll):
    # To prevent deleting standalone votes..
    if 'votes' in new and not new['votes']:
        del new['votes']

    # need_save = something has changed
    # updated = the updated_at field needs bumping
    # (we don't bump updated_at if only the sources list has changed, but
    #  we still update the object)
    need_save, updated = False, False

    locked_fields = old.get('_locked_fields', [])

    for key, value in new.items():

        if key in locked_fields:
            continue

        if old.get(key) != value:
            old[key] = value

            need_save = True
            if key != 'sources':
                updated = True

        # remove old +key field if this field no longer has a +
        plus_key = '+%s' % key
        if plus_key in old:
            del old[plus_key]
            need_save, updated = True, True

    if updated:
        old['updated_at'] = datetime.datetime.utcnow()

    if need_save:
        coll.save(old, safe=True)


def convert_timestamps(obj):
    """
    Convert unix timestamps in the scraper output to python datetimes
    so that they will be saved properly as Mongo datetimes.
    """
    for key in ('date', 'when', 'end', 'start_date', 'end_date',
                'retrieved'):
        value = obj.get(key)
        if value:
            obj[key] = timestamp_to_dt(value)

    for key in ('sources', 'actions', 'votes'):
        for child in obj.get(key, []):
            convert_timestamps(child)

    for term in obj.get('terms', []):
        convert_timestamps(term)

    for details in obj.get('session_details', {}).values():
        convert_timestamps(details)

    for role in obj.get('roles', []):
        convert_timestamps(role)
        role['state'] = obj['state']

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


__committee_ids = {}


def get_committee_id(state, chamber, committee):
    key = (state, chamber, committee)
    if key in __committee_ids:
        return __committee_ids[key]

    comms = db.committees.find({'state': state,
                               'chamber': chamber,
                               'committee': committee,
                               'subcommittee': None})

    if comms.count() != 1:
        comms = db.committees.find({'state': state,
                                   'chamber': chamber,
                                   'committee': ('Committee on ' +
                                                 committee),
                                   'subcommittee': None})

    if comms and comms.count() == 1:
        __committee_ids[key] = comms[0]['_id']
    else:
        __committee_ids[key] = None

    return __committee_ids[key]


def put_document(doc, content_type, metadata):
    # Generate a new sequential ID for the document
    query = SON([('_id', metadata['bill']['state'])])
    update = SON([('$inc', SON([('seq', 1)]))])
    seq = db.command(SON([('findandmodify', 'doc_ids'),
                          ('query', query),
                          ('update', update),
                          ('new', True),
                          ('upsert', True)]))['value']['seq']

    id = "%sD%08d" % (metadata['bill']['state'].upper(), seq)
    logging.info("Saving as %s" % id)

    fs.put(doc, _id=id, content_type=content_type, metadata=metadata)

    return id


def merge_legislators(old, new):
    all_ids = set(old['_all_ids']).union(new['_all_ids'])
    new['_all_ids'] = list(all_ids)
    db.legislators.remove({'_id': new['_id']})
    new['_id'] = old['_id']
    new['leg_id'] = new['_id']
    db.legislators.save(new)

# fixing bill ids
_bill_id_re = re.compile(r'([A-Z]*)\s*0*([-\d]+)')
def fix_bill_id(bill_id):
    bill_id = bill_id.replace('.', '')
    return _bill_id_re.sub(r'\1 \2', bill_id)


class VoteMatcher(object):

    def __init__(self, state):
        self.state = state
        self.vote_ids = {}

    def reset_sequence(self):
        self.seq_for_vote_key = defaultdict(int)

    def get_next_id(self):
        # Generate a new sequential ID for the vote
        query = SON([('_id', self.state)])
        update = SON([('$inc', SON([('seq', 1)]))])
        seq = db.command(SON([('findandmodify', 'vote_ids'),
                              ('query', query),
                              ('update', update),
                              ('new', True),
                              ('upsert', True)]))['value']['seq']

        return "%sV%08d" % (self.state.upper(), seq)

    def key_for_vote(self, vote):
        key = (vote['motion'], vote['chamber'], vote['date'],
               vote['yes_count'], vote['no_count'], vote['other_count'])
        # running count of how many of this key we've seen
        seq_num = self.seq_for_vote_key[key]
        self.seq_for_vote_key[key] += 1
        # append seq_num to key to avoid sharing key for multiple votes
        return key + (seq_num,)

    def learn_vote_ids(self, votes_list):
        self.reset_sequence()
        for vote in votes_list:
            key = self.key_for_vote(vote)
            self.vote_ids[key] = vote['vote_id']

    def set_vote_ids(self, votes_list):
        self.reset_sequence()
        for vote in votes_list:
            key = self.key_for_vote(vote)
            vote['vote_id'] = self.vote_ids.get(key) or self.get_next_id()
