#!/usr/bin/env python
import re
import os
import sys
import time
import zipfile
import datetime
import urllib2
import urllib

try:
    import json
except:
    import simplejson as json

from billy import settings
from billy import db

import boto
import pymongo
import scrapelib
import validictory
from boto.s3.key import Key


class APIValidator(validictory.SchemaValidator):
    def validate_type_datetime(self, val):
        if not isinstance(val, basestring):
            return False

        return re.match(r'^\d{4}-\d\d-\d\d( \d\d:\d\d:\d\d)?$', val)


_base_url = getattr(settings, 'OPENSTATES_API_BASE_URL',
                    "http://openstates.sunlightlabs.com/api/v1/")

def api_url(path):
    return "%s%s/?apikey=%s" % (_base_url, urllib.quote(path),
                                settings.SUNLIGHT_SERVICES_KEY)


def dump_json(state, filename, validate):
    scraper = scrapelib.Scraper(requests_per_minute=600)

    zip = zipfile.ZipFile(filename, 'w')

    cwd = os.path.split(__file__)[0]

    with open(os.path.join(cwd, "../schemas/api/bill.json")) as f:
        bill_schema = json.load(f)

    with open(os.path.join(cwd, "../schemas/api/legislator.json")) as f:
        legislator_schema = json.load(f)

    with open(os.path.join(cwd, "../schemas/api/committee.json")) as f:
        committee_schema = json.load(f)

    for bill in db.bills.find({'state': state}):
        path = "bills/%s/%s/%s/%s" % (state, bill['session'],
                                           bill['chamber'],
                                           bill['bill_id'])
        url = api_url(path)

        response = scraper.urlopen(url)
        if validate:
            validictory.validate(json.loads(response), bill_schema,
                                 validator_cls=APIValidator)

        zip.writestr(path, scraper.urlopen(url))

    for legislator in db.legislators.find({'state': state}):
        path = 'legislators/%s' % legislator['_id']
        url = api_url(path)

        response = scraper.urlopen(url)
        if validate:
            validictory.validate(json.loads(response), legislator_schema,
                                 validator_cls=APIValidator)

        zip.writestr(path, response)

    for committee in db.committees.find({'state': state}):
        path = 'committees/%s' % committee['_id']
        url = api_url(path)

        response = scraper.urlopen(url)
        if validate:
            validictory.validate(json.loads(response), committee_schema,
                                 validator_cls=APIValidator)

        zip.writestr(path, response)

    zip.close()


def upload(state, filename):
    date = datetime.date.today()
    year = date.year
    month = date.month - 1
    if month == 0:
        month = 12
        year -= 1

    # build URL
    s3_bucket = 'data.openstates.sunlightlabs.com'
    n = 1
    s3_path = '%s-%02d-%s-r%d.zip' % (year, month, state, n)
    s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)

    metadata = db.metadata.find_one({'_id':state})
    old_url = metadata.get('latest_dump_url')

    if s3_url == old_url:
        old_num = re.match('.*?-r(\d*).zip', old_url).groups()[0]
        n = int(old_num)+1
        s3_path = '%s-%02d-%s-r%d.zip' % (year, month, state, n)
        s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)

    # S3 upload
    s3conn = boto.connect_s3(settings.AWS_KEY, settings.AWS_SECRET)
    bucket = s3conn.create_bucket(s3_bucket)
    k = Key(bucket)
    k.key = s3_path
    k.set_contents_from_filename(filename)
    k.set_acl('public-read')

    metadata['latest_dump_url'] = s3_url
    metadata['latest_dump_date'] = datetime.datetime.utcnow()
    db.metadata.save(metadata, safe=True)

    print 'uploaded to %s' % s3_url


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description=('Dump API contents of a given state to a zipped'
                     ' directory of JSON files, optionally uploading'
                     ' to S3 when done.'))
    parser.add_argument('state', help=('the two-letter abbreviation of the'
                                       ' state to import'))
    parser.add_argument('--file', '-f',
                        help='filename to output to (defaults to <state>.zip)')
    parser.add_argument('--nodump', action='store_true', default=False,
                        help="don't run the dump, only upload")
    parser.add_argument('--novalidate', action='store_true', default=False,
                        help="don't run validation")
    parser.add_argument('--upload', '-u', action='store_true', default=False,
                        help='upload the created archive to S3')

    args = parser.parse_args()

    if not args.file:
        args.file = args.state + '.zip'

    if not args.nodump:
        dump_json(args.state, args.file, not args.novalidate)

    if args.upload:
        upload(args.state, args.file)
