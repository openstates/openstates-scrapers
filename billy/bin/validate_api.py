#!/usr/bin/env python
import os
import json
import random
import subprocess

from billy import db
from billy.bin.dump_json import APIValidator, api_url

import scrapelib
import lxml.etree
import validictory


def get_xml_schema():
    cwd = os.path.split(__file__)[0]
    schema_dir = os.path.join(cwd, "../schemas/relax/")

    rnc_path = os.path.join(schema_dir, 'api.rnc')
    rng_path = os.path.join(schema_dir, 'api_gen.rng')

    subprocess.check_call(["trang", rnc_path, rng_path])

    with open(rng_path) as f:
        schema = lxml.etree.RelaxNG(lxml.etree.parse(f))

    return schema


def validate_api(state):
    cwd = os.path.split(__file__)[0]
    schema_dir = os.path.join(cwd, "../schemas/api/")

    xml_schema = get_xml_schema()

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
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), bill_schema,
                                 validator_cls=APIValidator)

        xml_response = scrapelib.urlopen(url + "&format=xml")
        xml = lxml.etree.fromstring(xml_response)
        for child in xml.xpath("/results/*"):
            xml_schema.assertValid(child)

    with open(os.path.join(schema_dir, "legislator.json")) as f:
        legislator_schema = json.load(f)

    for legislator in db.legislators.find({'state': state}):
        path = 'legislators/%s' % legislator['_id']
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), legislator_schema,
                             validator_cls=APIValidator)

        xml_response = scrapelib.urlopen(url + "&format=xml")
        xml = lxml.etree.fromstring(xml_response)
        for child in xml.xpath("/results/*"):
            xml_schema.assertValid(child)

    with open(os.path.join(schema_dir, "committee.json")) as f:
        committee_schema = json.load(f)

    for committee in db.committees.find({'state': state}):
        path = "committees/%s" % committee['_id']
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), committee_schema,
                             validator_cls=APIValidator)

        xml_response = scrapelib.urlopen(url + "&format=xml")
        xml = lxml.etree.fromstring(xml_response)
        for child in xml.xpath("/results/*"):
            xml_schema.assertValid(child)


if __name__ == '__main__':
    import sys
    validate_api(sys.argv[1])
