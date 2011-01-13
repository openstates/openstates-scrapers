#!/usr/bin/env python
from billy import db
from pymongo.code import Code


def unique_sources(state=None):
    """
    Return a list of (URL, count) pairs with the URL and number of appearances
    of each unique source in the database.
    """
    m = Code("""
    function() {
        for (var i in this['sources']) {
            var source = this['sources'][i];
            emit(source['url'], 1);
        }
    }""")

    r = Code("""
    function(key, values) {
        var sum = 0;
        for (var i in values) sum += values[i];
        return sum;
    }""")

    query = {}
    if state:
        query['state'] = state

    collection = db.bills.map_reduce(m, r, query=query)

    return [(s['_id'], int(s['value'])) for s in collection.find()]


if __name__ == '__main__':
    import sys
    import csv

    try:
        state = sys.argv[1]
    except IndexError:
        state = None

    out = csv.writer(sys.stdout)
    out.writerow(("URL", "Count"))

    for row in unique_sources(state):
        out.writerow(row)
