#!/usr/bin/env python
from billy import db
from pymongo.code import Code


def generate_statistics():
    """
    Use mongo's map/reduce to output counts of various objects to the 'counts'
    collection.
    """
    m = Code("""
    function () {

        var val = {'bills': 1,
                   'introduced': 0,
                   'categorized': 0,
                   'actions_this_term': 0,
                   'voters': 0,
                   'idd_voters': 0,
                   'actions': this.actions.length,
                   'votes': this.votes.length,
                   'versions': this.versions.length};

        if(this.hasOwnProperty('subjects') && this['subjects'].length > 0) {
             val['subjects'] = 1;
        } else {
             val['subjects'] = 0;
        }

        // only do remaining calculations for current term
        if(this['_current_term']) {

            val['actions_this_term'] = val['actions'];

            // count how many actions are categorized & introduced
            for(var i=0; i < this.actions.length; ++i) {
                if(this.actions[i]["type"] != "other") {
                    val['categorized']++;
                }
                for(var j=0; j < this.actions[i]["type"].length; ++j) {
                    if(this.actions[i]["type"][j] == "bill:introduced") {
                        val['introduced'] = 1;
                    }
                }
            }

            // check sponsor leg_ids
            val['sponsors'] = this.sponsors.length;
            val['idd_sponsors'] = 0;

            for(var i=0; i < this.sponsors.length; ++i) {
                 if(this.sponsors[i]['leg_id']) {
                     val['idd_sponsors'] += 1;
                 }
            }

            // go through yes/no/other votes and count voter leg_ids
            for(var i=0; i < this.votes.length; ++i) {
                for(var j=0; j < this.votes[i]["yes_votes"].length; ++j) {
                    val['voters'] += 1;
                    if(this.votes[i]["yes_votes"][j]["leg_id"]) {
                        val['idd_voters'] += 1;
                    }
                }
            }
            for(var i=0; i < this.votes.length; ++i) {
                for(var j=0; j < this.votes[i]["no_votes"].length; ++j) {
                    val['voters'] += 1;
                    if(this.votes[i]["no_votes"][j]["leg_id"]) {
                        val['idd_voters'] += 1;
                    }
                }
            }
            for(var i=0; i < this.votes.length; ++i) {
                for(var j=0; j < this.votes[i]["other_votes"].length; ++j) {
                    val['voters'] += 1;
                    if(this.votes[i]["other_votes"][j]["leg_id"]) {
                        val['idd_voters'] += 1;
                    }
                }
            }
        }

        // emit either way
        emit(this[this['level']], val);
        emit('total', val);
    }""")

    r = Code("""
    function (key, values) {
        sums = {'bills': 0, 'actions': 0, 'votes': 0, 'versions': 0,
                'subjects': 0, 'introduced': 0, 'categorized': 0,
                'voters': 0, 'idd_voters': 0, 'actions_this_term': 0,
                'sponsors': 0, 'idd_sponsors': 0};
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
