import os
import sys
import time
import zipfile
import datetime

try:
    import json
except:
    import simplejson as json

from fiftystates.backend import db

import pymongo
import boto
from boto.s3.key import Key

from django.core.management.base import BaseCommand, make_option
from django.contrib.redirects.models import Redirect
from django.conf import settings

class FiftyStateEncoder(json.JSONEncoder):
    """
    JSONEncoder that encodes datetime objects as Unix timestamps
    and Mongo ObjectIDs as hex encoded strings.
    """

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return time.mktime(obj.timetuple())
        if isinstance(obj, pymongo.objectid.ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def dump_json(state, filename):
    zip = zipfile.ZipFile(filename, 'w')

    for bill in db.bills.find({'state': state}):
        path = "/api/%s/%s/%s/bills/%s" % (state, bill['session'],
                                           bill['chamber'],
                                           bill['bill_id'])

        zip.writestr(path, json.dumps(bill, cls=FiftyStateEncoder))

    for legislator in db.legislators.find({'state': state}):
        path = '/api/legislators/%s' % legislator['_id']

        zip.writestr(path, json.dumps(legislator, cls=FiftyStateEncoder))

    for committee in db.committees.find({'state': state}):
        path = '/api/committees/%s' % committee['_id']

        zip.writestr(path, json.dumps(committee, cls=FiftyStateEncoder))

    zip.close()


def upload(state, filename):
    date = datetime.date.today()
    year = date.year
    month = date.month - 1
    if month == 0:
        month = 12
        year -= 1

    s3_bucket = 'data.openstates.sunlightlabs.com'
    s3_path = '%s-%02d-%s.zip' % (year, month, state)
    s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)
    n = 1

    while Redirect.objects.filter(new_path=s3_url).count():
        s3_path = '%s-%02d-%s-update%s.zip' % (year, month, state, n)
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


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--upload', action='store_true', dest='upload',
                    default=False, help='Upload created file'),
    )

    def handle(self, *args, **options):
        try:
            state = args[0].lower()
        except IndexError:
            print ("Please provide a state abbreviation as the first "
                   "argument.")
            sys.exit(1)

        if len(args) > 1:
            filename = args[1]
        else:
            filename = state + '.zip'

        dump_json(state, filename)

        if options.get('upload'):
            upload(state, filename)
