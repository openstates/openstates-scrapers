#!/usr/bin/env python
from billy import db
from pymongo.code import Code


def generate_statistics():
    """
    Use mongo's map/reduce to output state-by-state (and total) counts of
    various Open State objects to the 'counts' collection.
    """
    m = Code("""
    function () {
        var val = {'bills': 1,
                   'introduced': 0,
                   'categorized': 0,
                   'actions': this.actions.length,
                   'votes': this.votes.length,
                   'versions': this.versions.length};

        for(var i=0; i < this.actions.length; ++i) {
            if(this.actions[i]["type"] != ["other"]) {
                val['categorized']++;
            }
            for(var j=0; j < this.actions[i].length; ++j) {
                if(this.actions[i][j]["type"] == "bill:introduced") {
                    val['introduced'] = 1;
                }
            }
        }
        emit(this['state'], val);
        emit('total', val);
    }""")

    r = Code("""
    function (key, values) {
        sums = {'bills': 0, 'actions': 0, 'votes': 0, 'versions': 0,
                'introduced': 0, 'categorized': 0};
        for (var i in values) {
            value = values[i];

            for (var t in value) {
                sums[t] += value[t];
            }
        }

        return sums;
    }""")

    # a finalizer to convert all counts from JS numbers (floats) to longs
    f = Code("""
    function (key, value) {
        for (var t in value) {
            value[t] = new NumberLong(value[t]);
        }

        return value;
    }""")

    db.bills.map_reduce(m, r, finalize=f, out='counts')


if __name__ == '__main__':
    generate_statistics()
