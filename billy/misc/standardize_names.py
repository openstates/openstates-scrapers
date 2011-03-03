#!/usr/bin/env python
from billy import db, utils


_leg_names = {}
for legislator in db.legislators.find():
    _leg_names[legislator['_id']] = legislator['full_name']


def standardize_names(state):
    for bill in db.bills.find({'state': state}):
        for vote in bill['votes']:
            for sv in vote['yes_votes']:
                try:
                    sv['name'] = _leg_names[sv['leg_id']]
                except KeyError:
                    pass
            for sv in vote['no_votes']:
                try:
                    sv['name'] = _leg_names[sv['leg_id']]
                except KeyError:
                    pass
            for sv in vote['other_votes']:
                try:
                    sv['name'] = _leg_names[sv['leg_id']]
                except KeyError:
                    pass

        for sponsor in bill['sponsors']:
            try:
                sponsor['name'] = _leg_names[sponsor['leg_id']]
            except KeyError:
                pass

        db.bills.save(bill)


if __name__ == '__main__':
    import sys
    standardize_names(sys.argv[1])
