#!/usr/bin/env python
import os
import json
import random
import subprocess

from billy import db
from billy.utils import metadata
from billy.conf import settings, base_arg_parser
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


def get_json_schema(name, schema_dir):
    if schema_dir:
        try:
            schema_dir = os.path.abspath(schema_dir)
            with open(os.path.join(schema_dir, name + ".json")) as f:
                return json.load(f)
        except IOError as ex:
            if ex.errno != 2:
                raise

    # Fallback to default schema dir
    cwd = os.path.split(__file__)[0]
    default_schema_dir = os.path.join(cwd, "../schemas/api/")

    with open(os.path.join(default_schema_dir, name + ".json")) as f:
        return json.load(f)


def validate_api(abbr, schema_dir=None):
    xml_schema = get_xml_schema()

    metadata_schema = get_json_schema("metadata", schema_dir)
    path = "metadata/%s" % abbr
    url = api_url(path)
    json_response = scrapelib.urlopen(url)
    validictory.validate(json.loads(json_response), metadata_schema,
                         validator_cls=APIValidator)
    validate_xml(url, xml_schema)

    bill_schema = get_json_schema("bill", schema_dir)

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

    legislator_schema = get_json_schema("legislator", schema_dir)
    for legislator in db.legislators.find(spec):
        path = 'legislators/%s' % legislator['_id']
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), legislator_schema,
                             validator_cls=APIValidator)

        validate_xml(url, xml_schema)

    committee_schema = get_json_schema("committee", schema_dir)
    for committee in db.committees.find(spec):
        path = "committees/%s" % committee['_id']
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), committee_schema,
                             validator_cls=APIValidator)

        validate_xml(url, xml_schema)

    event_schema = get_json_schema("event", schema_dir)
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
    import argparse

    parser = argparse.ArgumentParser(description='validate API results',
                                     parents=[base_arg_parser])
    parser.add_argument('states', nargs='+', help='states to validate')
    parser.add_argument('--schema_dir',
                        help='directory to use for API schemas (optional)',
                        default=None)
    args = parser.parse_args()
    settings.update(args)

    for state in args.states:
        print "Validating %s" % state
        validate_api(state, args.schema_dir)
