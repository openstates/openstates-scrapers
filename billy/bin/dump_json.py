#!/usr/bin/env python
import datetime
import json
import logging
import os
import re
import urllib
import zipfile

from billy.conf import settings, base_arg_parser
from billy.utils import metadata, configure_logging
from billy import db

import boto
import scrapelib
import validictory
from boto.s3.key import Key


class APIValidator(validictory.SchemaValidator):
    def validate_type_datetime(self, val):
        if not isinstance(val, basestring):
            return False

        return re.match(r'^\d{4}-\d\d-\d\d( \d\d:\d\d:\d\d)?$', val)


def api_url(path):
    return "%s%s/?apikey=%s" % (settings.API_BASE_URL, urllib.quote(path),
                                settings.SUNLIGHT_SERVICES_KEY)


def dump_json(abbr, filename, validate, schema_dir):
    scraper = scrapelib.Scraper(requests_per_minute=600, follow_robots=False)
    level = metadata(abbr)['level']

    zip = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED)

    if not schema_dir:
        cwd = os.path.split(__file__)[0]
        schema_dir = os.path.join(cwd, "../schemas/api/")

    with open(os.path.join(schema_dir, "bill.json")) as f:
        bill_schema = json.load(f)

    with open(os.path.join(schema_dir, "legislator.json")) as f:
        legislator_schema = json.load(f)

    with open(os.path.join(schema_dir, "committee.json")) as f:
        committee_schema = json.load(f)

    logging.info('dumping %s bills...' % abbr)
    for bill in db.bills.find({'level': level, level: abbr}, timeout=False):
        path = "bills/%s/%s/%s/%s" % (abbr, bill['session'],
                                      bill['chamber'], bill['bill_id'])
        url = api_url(path)

        response = scraper.urlopen(url)
        if validate:
            validictory.validate(json.loads(response), bill_schema,
                                 validator_cls=APIValidator)

        zip.writestr(path, response)

    logging.info('dumping %s legislators...' % abbr)
    for legislator in db.legislators.find({'level': level, level: abbr}):
        path = 'legislators/%s' % legislator['_id']
        url = api_url(path)

        response = scraper.urlopen(url)
        if validate:
            validictory.validate(json.loads(response), legislator_schema,
                                 validator_cls=APIValidator)

        zip.writestr(path, response)

    logging.info('dumping %s committees...' % abbr)
    for committee in db.committees.find({'level': level, level: abbr}):
        path = 'committees/%s' % committee['_id']
        url = api_url(path)

        response = scraper.urlopen(url)
        if validate:
            validictory.validate(json.loads(response), committee_schema,
                                 validator_cls=APIValidator)

        zip.writestr(path, response)

    zip.close()


def upload(abbr, filename):
    today = datetime.date.today()

    # build URL
    s3_bucket = settings.AWS_BUCKET
    s3_path = '%s-%02d-%02d-%s.zip' % (today.year, today.month, today.day,
                                           abbr)
    s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)

    meta = metadata(abbr)

    # S3 upload
    s3conn = boto.connect_s3(settings.AWS_KEY, settings.AWS_SECRET)
    bucket = s3conn.create_bucket(s3_bucket)
    k = Key(bucket)
    k.key = s3_path
    logging.info('beginning upload to %s' % s3_url)
    k.set_contents_from_filename(filename)
    k.set_acl('public-read')

    meta['latest_dump_url'] = s3_url
    meta['latest_dump_date'] = datetime.datetime.utcnow()
    db.metadata.save(meta, safe=True)

    logging.info('upload complete')


def main():
    import argparse

    configure_logging(1)

    parser = argparse.ArgumentParser(
        description=('Dump API information to a zipped directory of JSON files'
                     ', optionally uploading to S3 when done.'),
        parents=[base_arg_parser],
    )
    parser.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                help=('the two-letter abbreviation for the data to export'))
    parser.add_argument('--file', '-f',
                        help='filename to output to (defaults to <abbr>.zip)')
    parser.add_argument('--schema_dir',
                        help='directory to use for API schemas (optional)',
                        default=None)
    parser.add_argument('--nodump', action='store_true', default=False,
                        help="don't run the dump, only upload")
    parser.add_argument('--novalidate', action='store_true', default=False,
                        help="don't run validation")
    parser.add_argument('--upload', '-u', action='store_true', default=False,
                        help='upload the created archive to S3')

    args = parser.parse_args()

    settings.update(args)

    for abbr in args.abbrs:
        if not args.file:
            args.file = abbr + '.zip'

        if not args.nodump:
            dump_json(abbr, args.file, not args.novalidate, args.schema_dir)

        if args.upload:
            upload(abbr, args.file)


if __name__ == '__main__':
    main()
