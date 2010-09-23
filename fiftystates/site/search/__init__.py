import re

from fiftystates.backend import db
from fiftystates.utils import keywordize


def bill_query(str, params, fields=None, all=True, limit=None, skip=None,
               sort=None):
    keywords = list(keywordize(str))

    filter = {}

    if all:
        filter['_keywords'] = {'$all': keywords}
    else:
        filter['_keywords'] = {'$in': keywords}

    for key in ('state', 'session', 'chamber'):
        value = params.get(key)
        if value:
            filter[key] = value

    cursor = db.bills.find(filter, fields)

    if limit:
        cursor.limit(limit)

    if skip:
        cursor.skip(skip)

    if sort:
        cursor.sort(sort)

    return list(cursor)
