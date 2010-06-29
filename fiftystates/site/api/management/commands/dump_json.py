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

from django.core.management.base import BaseCommand


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


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            self.state_abbrev = args[0].lower()
        except IndexError:
            print ("Please provide a state abbreviation as the first "
                   "argument.")
            sys.exit(1)

        self.dump_json()

    def dump_json(self):
        zip = zipfile.ZipFile('%s.zip' % self.state_abbrev, 'w')

        for bill in db.bills.find({'state': self.state_abbrev}):
            path = "/api/%s/%s/%s/bills/%s" % (
                self.state_abbrev, bill['session'], bill['chamber'],
                bill['bill_id'])

            zip.writestr(path, json.dumps(bill, cls=FiftyStateEncoder))

        for legislator in db.legislators.find({'state': self.state_abbrev}):
            path = '/api/legislators/%s' % legislator['_id']

            zip.writestr(path, json.dumps(legislator, cls=FiftyStateEncoder))

        zip.close()
