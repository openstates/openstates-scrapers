#!/usr/bin/env python
import os
import json
import random

from billy import db
from billy.bin.dump_json import APIValidator, api_url

import scrapelib
import validictory


def validate_api(state):
    cwd = os.path.split(__file__)[0]
    schema_dir = os.path.join(cwd, "../schemas/api/")

    with open(os.path.join(schema_dir, "metadata.json")) as f:
        metadata_schema = json.load(f)

    path = "metadata/%s" % state
    response = scrapelib.urlopen(api_url(path))
    validictory.validate(json.loads(response), metadata_schema,
                         validator_cls=APIValidator)

    with open(os.path.join(schema_dir, "bill.json")) as f:
        bill_schema = json.load(f)

    bill_spec = {'state': state}
    total_bills = db.bills.find(bill_spec).count()

    for i in xrange(0, 100):
        bill = db.bills.find(bill_spec)[random.randint(0, total_bills - 1)]
        path = "bills/%s/%s/%s/%s" % (state, bill['session'],
                                           bill['chamber'],
                                           bill['bill_id'])
        response = scrapelib.urlopen(api_url(path))
        validictory.validate(json.loads(response), bill_schema,
                                 validator_cls=APIValidator)

    with open(os.path.join(schema_dir, "legislator.json")) as f:
        legislator_schema = json.load(f)

    for legislator in db.legislators.find({'state': state}):
        path = 'legislators/%s' % legislator['_id']
        response = scrapelib.urlopen(api_url(path))
        validictory.validate(json.loads(response), legislator_schema,
                             validator_cls=APIValidator)

    with open(os.path.join(schema_dir, "committee.json")) as f:
        committee_schema = json.load(f)

    for committee in db.committees.find({'state': state}):
        path = "committees/%s" % committee['_id']
        response = scrapelib.urlopen(api_url(path))
        validictory.validate(json.loads(response), committee_schema,
                             validator_cls=APIValidator)


if __name__ == '__main__':
    import sys
    validate_api(sys.argv[1])
