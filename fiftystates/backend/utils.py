import re
import time
import datetime

from fiftystates.backend import db

import nltk
import argparse
import name_tools

base_arg_parser = argparse.ArgumentParser(add_help=False)
base_arg_parser.add_argument('state', type=str,
                             help=('the two-letter abbreviation of the '
                                   'state to import'))


def keywordize(str):
    """
    Splits a string into words, removes common stopwords, stems and removes
    duplicates.
    """
    sents = nltk.tokenize.sent_tokenize(str)

    words = []
    for sent in sents:
        words.extend(nltk.tokenize.word_tokenize(sent))

    stemmer = nltk.stem.porter.PorterStemmer()
    stop_words = nltk.corpus.stopwords.words("english")
    words = [stemmer.stem(word.lower()) for word in words if
             (word.isalpha() or word.isdigit()) and
             word.lower() not in stop_words]
    words = set(words)

    return words


def insert_with_id(obj):
    """
    Generates a unique ID for the supplied legislator/committee/bill
    and inserts it into the appropriate collection.
    """
    if hasattr(obj, '_id'):
        raise ValueError("object already has '_id' field")

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
    while True:
        cursor = collection.find({'_id': id_reg}).sort('_id', -1).limit(1)

        try:
            prev_id = cursor.next()['_id']
            obj['_id'] = "%s%06d" % (prev_id[0:3], int(prev_id[3:]) + 1)
        except StopIteration:
            obj['_id'] = "%s%s000001" % (obj['state'].upper(), id_type)

        all_ids = obj.get('_all_ids', [])
        if obj['_id'] not in all_ids:
            all_ids.append(obj['_id'])
        obj['_all_ids'] = all_ids

        if obj['_type'] in ['person', 'legislator']:
            obj['leg_id'] = obj['_id']

        try:
            return collection.insert(obj, safe=True)
        except pymongo.DuplicateKeyError:
            continue


def timestamp_to_dt(timestamp):
    return datetime.datetime(*time.localtime(timestamp)[0:6])


def update(old, new, coll):
    # To prevent deleting standalone votes..
    if 'votes' in new and not new['votes']:
        del new['votes']

    changed = False
    for key, value in new.items():
        if old.get(key) != value:
            old[key] = value
            changed = True

    if changed:
        old['updated_at'] = datetime.datetime.now()
        coll.save(old, safe=True)


def prepare_obj(obj):
    """
    Convert timestamps in the scraper output to datetimes so that they
    will be saved as Mongo datetimes, and standardize some other fields.
    """
    for source in obj.get('sources', []):
        source['retrieved'] = timestamp_to_dt(source['retrieved'])

    for action in obj.get('actions', []):
        action['date'] = timestamp_to_dt(action['date'])

    for role in obj.get('roles', []):
        if role['start_date']:
            role['start_date'] = timestamp_to_dt(role['start_date'])

        if role['end_date']:
            role['end_date'] = timestamp_to_dt(role['end_date'])

        role['state'] = obj['state']

    for vote in obj.get('votes', []):
        vote['date'] = timestamp_to_dt(vote['date'])

    if 'date' in obj:
        obj['date'] = timestamp_to_dt(obj['date'])

    # If we are handling a legislator and the scraped data
    # includes both 'first_name' and 'last_name' fields, then use them.
    # If one or both of these fields is missing, then run the name_tools
    # splitting code to generate them.
    if obj['_type'] in ('person', 'legislator'):
        split_name = False
        for key in ('first_name', 'last_name'):
            if key not in obj or not obj[key]:
                # Need to split
                (obj['first_name'], obj['last_name'],
                 obj['suffixes']) = name_tools.split(obj['full_name'])[1:]
                break

    return obj
