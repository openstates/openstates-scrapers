#!/usr/bin/env python
import os
import json
import random
import subprocess

from billy import db
from billy.utils import metadata
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


def validate_xml(url, schema):
    response = scrapelib.urlopen(url + "&format=xml")
    xml = lxml.etree.fromstring(response)
    for child in xml.xpath("/results/*"):
        schema.assertValid(child)


def validate_api(abbr):
    cwd = os.path.split(__file__)[0]
    schema_dir = os.path.join(cwd, "../schemas/api/")

    xml_schema = get_xml_schema()

    with open(os.path.join(schema_dir, "metadata.json")) as f:
        metadata_schema = json.load(f)

    path = "metadata/%s" % abbr
    url = api_url(path)
    json_response = scrapelib.urlopen(url)
    validictory.validate(json.loads(json_response), metadata_schema,
                         validator_cls=APIValidator)
    validate_xml(url, xml_schema)

    with open(os.path.join(schema_dir, "bill.json")) as f:
        bill_schema = json.load(f)

    level = metadata(abbr)['level']
    spec = {'level': level, level: abbr}
    total_bills = db.bills.find(spec).count()

    for i in xrange(0, 100):
        bill = db.bills.find(spec)[random.randint(0, total_bills - 1)]
        path = "bills/%s/%s/%s/%s" % (abbr, bill['session'],
                                      bill['chamber'], bill['bill_id'])
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), bill_schema,
                                 validator_cls=APIValidator)

        validate_xml(url, xml_schema)

    with open(os.path.join(schema_dir, "legislator.json")) as f:
        legislator_schema = json.load(f)

    for legislator in db.legislators.find(spec):
        path = 'legislators/%s' % legislator['_id']
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), legislator_schema,
                             validator_cls=APIValidator)

        validate_xml(url, xml_schema)

    with open(os.path.join(schema_dir, "committee.json")) as f:
        committee_schema = json.load(f)

    for committee in db.committees.find(spec):
        path = "committees/%s" % committee['_id']
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), committee_schema,
                             validator_cls=APIValidator)

        validate_xml(url, xml_schema)

    with open(os.path.join(schema_dir, "event.json")) as f:
        event_schema = json.load(f)

    total_events = db.events.find(spec).count()

    if total_events:
        for i in xrange(0, 10):
            event = db.events.find(spec)[random.randint(0, total_events - 1)]
            path = "events/%s" % event['_id']
            url = api_url(path)

            json_response = scrapelib.urlopen(url)
            validictory.validate(json.loads(json_response), event_schema,
                                 validator_cls=APIValidator)

            validate_xml(url, xml_schema)


if __name__ == '__main__':
    import sys
    validate_api(sys.argv[1])
