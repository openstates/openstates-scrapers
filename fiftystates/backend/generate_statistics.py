#!/usr/bin/env python
from fiftystates.backend import db
from pymongo.code import Code


def generate_statistics():
    m = Code("""
    function () {
        var val = {'bills': 1,
                   'actions': this.actions.length,
                   'votes': this.votes.length,
                   'versions': this.versions.length};
        emit(this['state'], val);
        emit('total', val);
    }""")

    r = Code("""
    function (key, values) {
        sums = {'bills': 0, 'actions': 0, 'votes': 0, 'versions': 0};
        for (var i in values) {
            value = values[i];

            for (var t in value) {
                sums[t] += value[t];
            }
        }

        return sums;
    }""")

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
