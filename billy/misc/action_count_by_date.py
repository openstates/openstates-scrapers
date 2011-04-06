#!/usr/bin/env python
"""
Print a breakdown of action count by date for a given state.
"""
from billy import db


m = """
function map() {
    for (var i in this['actions']) {
        var action = this['actions'][i];
        emit(action['date'], 1);
    }
}"""


r = """
function reduce(key, values) {
    var sum = 0;
    for (var i in values) {
        sum += values[i];
    }
    return sum;
}"""


def action_count_by_date_mr(state):
    coll = db.bills.map_reduce(m, r, query={'state': state})
    return coll

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print "Please provide a state as an argument."
        sys.exit(1)

    coll = action_count_by_date_mr(sys.argv[1])

    for obj in coll.find():
        print "%s, %s" % (obj['_id'].date(), int(obj['value']))
