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

from fiftystates import settings
from fiftystates.backend import db

import pymongo
import boto
from boto.s3.key import Key
import validictory


class APIValidator(validictory.SchemaValidator):
    def validate_type_datetime(self, val):
        if not isinstance(val, basestring):
            return False

        return re.match(r'^\d{4}-\d\d-\d\d( \d\d:\d\d:\d\d)?$', val)


def api_url(path):
    return ("http://openstates.sunlightlabs.com/api/v1/" +
            urllib.quote(path) +
            "/?apikey=" + settings.SUNLIGHT_SERVICES_KEY)


def dump_json(state, filename):
    zip = zipfile.ZipFile(filename, 'w')

    cwd = os.path.split(__file__)[0]

    with open(os.path.join(cwd,
                           "../..//schemas/api/bill.json")) as f:
        bill_schema = json.load(f)

    with open(os.path.join(cwd,
                           "../../schemas/"
                           "api/legislator.json")) as f:
        legislator_schema = json.load(f)

    with open(os.path.join(cwd,
                           "../../schemas/"
                           "api/committee.json")) as f:
        committee_schema = json.load(f)

    for bill in db.bills.find({'state': state}):
        path = "api/%s/%s/%s/bills/%s" % (state, bill['session'],
                                           bill['chamber'],
                                           bill['bill_id'])

        url = api_url("bills/%s/%s/%s/%s" % (state,
                                             bill['session'],
                                             bill['chamber'],
                                             bill['bill_id']))

        response = urllib2.urlopen(url).read()
        validictory.validate(json.loads(response), bill_schema,
                             validator_cls=APIValidator)

        zip.writestr(path, urllib2.urlopen(url).read())

    for legislator in db.legislators.find({'state': state}):
        path = 'api/legislators/%s' % legislator['_id']
        url = api_url("legislators/" + legislator['_id'])

        response = urllib2.urlopen(url).read()
        validictory.validate(json.loads(response), legislator_schema,
                             validator_cls=APIValidator)

        zip.writestr(path, response)

    for committee in db.committees.find({'state': state}):
        path = 'api/committees/%s' % committee['_id']
        url = api_url("committees/" + committee['_id'])

        response = urllib2.urlopen(url).read()
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

    s3_bucket = 'data.openstates.sunlightlabs.com'
    n = 1
    s3_path = '%s-%02d-%s-r%d.zip' % (year, month, state, n)
    s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)

    while Redirect.objects.filter(new_path=s3_url).count():
        s3_path = '%s-%02d-%s-r%d.zip' % (year, month, state, n)
        s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)
        n += 1

    # S3 upload
    s3conn = boto.connect_s3(settings.AWS_KEY, settings.AWS_SECRET)
    bucket = s3conn.create_bucket(s3_bucket)
    k = Key(bucket)
    k.key = s3_path
    k.set_contents_from_filename(filename)
    k.set_acl('public-read')

    # create/update redirects
    old_path = '/data/%s.zip' % state
    redirect, created = Redirect.objects.get_or_create(old_path=old_path,
                                           defaults={'new_path':s3_url,
                                                     'site_id': 1})
    if not created:
        redirect.new_path = s3_url
        redirect.save()

    print 'redirect from %s to %s' % (redirect.old_path, redirect.new_path)


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
    parser.add_argument('--upload', '-u', action='store_true', default=False,
                        help='upload the created archive to S3')

    args = parser.parse_args()

    if not args.file:
        args.file = args.state + '.zip'

    dump_json(args.state, args.file)

    if args.upload:
        upload(args.state, args.file)
