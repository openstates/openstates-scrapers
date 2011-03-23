#!/usr/bin/env python
import re
import os
import csv
import time
import zipfile
import datetime

from billy import db
from billy.utils import extract_fields
from billy.conf import settings, base_arg_parser

import boto
import pymongo
from boto.s3.key import Key

def _make_csv(directory, name, fields):
    f = csv.DictWriter(open(os.path.join(directory, name), 'w'), fields)
    f.writerow(dict(zip(fields, fields)))
    return f

def dump_legislator_csvs(state, directory):
    leg_fields = ('leg_id', 'full_name', 'first_name', 'last_name',
                  'middle_name', 'suffixes', 'photo_url', 'active',
                  'created_at', 'updated_at')
    leg_csv = _make_csv(directory, 'legislators.csv', leg_fields)

    role_fields = ('leg_id', 'type', 'term', 'district', 'chamber', 'state',
                   'party', 'committee_id', 'committee', 'subcommittee',
                   'start_date', 'end_date')
    role_csv = _make_csv(directory, 'legislator_roles.csv', role_fields)

    for legislator in db.legislators.find({'state': state}):
        leg_csv.writerow(extract_fields(legislator, leg_fields))

        # go through roles to create role csv
        all_roles = legislator['roles']
        for roles in legislator.get('old_roles', {}).values():
            all_roles.extend(roles)

        for role in all_roles:
            d = extract_fields(role, role_fields)
            d.update({'leg_id':legislator['leg_id']})
            role_csv.writerow(d)

def dump_bill_csvs(state, directory):
    bill_fields = ('state', 'session', 'chamber', 'bill_id', 'title',
                   'created_at', 'updated_at', 'type', 'subjects')
    bill_csv = _make_csv(directory, 'bills.csv', bill_fields)

    action_fields = ('state', 'session', 'chamber', 'bill_id', 'date',
                     'action', 'actor', 'type')
    action_csv = _make_csv(directory, 'bill_actions.csv', action_fields)

    sponsor_fields = ('state', 'session', 'chamber', 'bill_id', 'type', 'name',
                      'leg_id')
    sponsor_csv = _make_csv(directory, 'bill_sponsors.csv', sponsor_fields)

    vote_fields = ('state', 'session', 'chamber', 'bill_id', 'vote_id',
                   'vote_chamber', 'motion', 'date', 'type', 'yes_count',
                   'no_count', 'other_count')
    vote_csv = _make_csv(directory, 'bill_votes.csv', vote_fields)

    legvote_fields = ('vote_id', 'leg_id', 'name', 'vote')
    legvote_csv = _make_csv(directory, 'bill_legislator_votes.csv',
                            legvote_fields)

    for bill in db.bills.find({'state': state}):
        bill_csv.writerow(extract_fields(bill, bill_fields))

        bill_info = extract_fields(bill,
                                   ('bill_id', 'state', 'session', 'chamber'))

        for action in bill['actions']:
            adict = extract_fields(action, action_fields)
            adict.update(bill_info)
            action_csv.writerow(adict)

        for sponsor in bill['sponsors']:
            sdict = extract_fields(sponsor, sponsor_fields)
            sdict.update(bill_info)
            sponsor_csv.writerow(sdict)

        for vote in bill['votes']:
            vdict = extract_fields(vote, vote_fields)
            # copy chamber from vote into vote_chamber
            vdict['vote_chamber'] = vdict['chamber']
            vdict.update(bill_info)
            vote_csv.writerow(vdict)

            for vtype in ('yes', 'no', 'other'):
                for leg_vote in vote[vtype+'_votes']:
                    legvote_csv.writerow({'vote_id': vote['vote_id'],
                                          'leg_id': leg_vote['leg_id'],
                                          'name': leg_vote['name'],
                                          'vote': vtype})


def dump_csv(state, directory):
    try:
        os.makedirs(directory)
    except OSError:
        pass

    dump_legislator_csvs(state, directory)
    dump_bill_csvs(state, directory)

def zjson_upload(state, filename):
    today = datetime.date.today()

    # build URL
    s3_bucket = 'data.openstates.sunlightlabs.com'
    n = 1
    s3_path = '%s-%02d-%s-r%d.zip' % (today.year, today.month, state, n)
    s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)

    metadata = db.metadata.find_one({'_id':state})
    old_url = metadata.get('latest_dump_url')

    if s3_url == old_url:
        old_num = re.match('.*?-r(\d*).zip', old_url).groups()[0]
        n = int(old_num)+1
        s3_path = '%s-%02d-%s-r%d.zip' % (today.year, today.month, state, n)
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
        description=('Dump API contents of a given state to  '
                     ' directory of CSV files, optionally uploading'
                     ' to S3 when done.'),
        parents=[base_arg_parser],
    )
    parser.add_argument('state', help=('the two-letter abbreviation of the'
                                       ' state to import'))
    parser.add_argument('--directory',
                        help='directory to output to (default: <state>_csv)')
    parser.add_argument('--nodump', action='store_true', default=False,
                        help="don't run the dump, only upload")
    parser.add_argument('--upload', '-u', action='store_true', default=False,
                        help='upload the created archive to S3')

    args = parser.parse_args()

    settings.update(args)

    if not args.directory:
        args.directory = args.state + '_csv'

    if not args.nodump:
        dump_csv(args.state, args.directory)

    if args.upload:
        upload(args.state, args.file)
