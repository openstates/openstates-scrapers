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

def _make_csv(state, name, fields):
    filename = '/tmp/{0}_{1}'.format(state, name)
    f = csv.DictWriter(open(filename, 'w'), fields)
    f.writerow(dict(zip(fields, fields)))
    return filename, f

def dump_legislator_csvs(state):
    leg_fields = ('leg_id', 'full_name', 'first_name', 'middle_name',
                  'last_name', 'suffixes', 'nickname', 'active',
                  'state', 'chamber', 'district', 'party',
                  'votesmart_id', 'transparencydata_id', 'photo_url',
                  'created_at', 'updated_at')
    leg_csv_fname, leg_csv = _make_csv(state, 'legislators.csv', leg_fields)

    role_fields = ('leg_id', 'type', 'term', 'district', 'chamber', 'state',
                   'party', 'committee_id', 'committee', 'subcommittee',
                   'start_date', 'end_date')
    role_csv_fname, role_csv = _make_csv(state, 'legislator_roles.csv',
                                         role_fields)

    com_fields = ('id', 'state', 'chamber', 'committee', 'subcommittee',
                  'parent_id')
    com_csv_fname, com_csv = _make_csv(state, 'committees.csv', com_fields)

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

    for committee in db.committees.find({'state': state}):
        cdict = extract_fields(committee, com_fields)
        cdict['id'] = committee['_id']
        com_csv.writerow(cdict)

    return leg_csv_fname, role_csv_fname, com_csv_fname

def dump_bill_csvs(state):
    bill_fields = ('state', 'session', 'chamber', 'bill_id', 'title',
                   'created_at', 'updated_at', 'type', 'subjects')
    bill_csv_fname, bill_csv = _make_csv(state, 'bills.csv', bill_fields)

    action_fields = ('state', 'session', 'chamber', 'bill_id', 'date',
                     'action', 'actor', 'type')
    action_csv_fname, action_csv = _make_csv(state, 'bill_actions.csv',
                                             action_fields)

    sponsor_fields = ('state', 'session', 'chamber', 'bill_id', 'type', 'name',
                      'leg_id')
    sponsor_csv_fname, sponsor_csv = _make_csv(state, 'bill_sponsors.csv',
                                               sponsor_fields)

    vote_fields = ('state', 'session', 'chamber', 'bill_id', 'vote_id',
                   'vote_chamber', 'motion', 'date', 'type', 'yes_count',
                   'no_count', 'other_count')
    vote_csv_fname, vote_csv = _make_csv(state, 'bill_votes.csv', vote_fields)

    legvote_fields = ('vote_id', 'leg_id', 'name', 'vote')
    legvote_csv_fname, legvote_csv = _make_csv(state,
                                               'bill_legislator_votes.csv',
                                               legvote_fields)

    for bill in db.bills.find({'state': state}):
        bill_csv.writerow(extract_fields(bill, bill_fields))

        bill_info = extract_fields(bill,
                                   ('bill_id', 'state', 'session', 'chamber'))

        # basically same behavior for actions, sponsors and votes:
        #    extract fields, update with bill_info, write to csv
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
                                      'name': leg_vote['name'].encode('utf8'),
                                      'vote': vtype})
    return (bill_csv_fname, action_csv_fname, sponsor_csv_fname,
            vote_csv_fname, legvote_csv_fname)

def dump_csv(state, filename):
    zfile = zipfile.ZipFile(filename, 'w')

    files = []
    files += dump_legislator_csvs(state)
    files += dump_bill_csvs(state)

    for fname in files:
        arcname = fname.split('/')[-1]
        zfile.write(fname, arcname=arcname)

def upload(state, filename):
    today = datetime.date.today()

    # build URL
    s3_bucket = 'data.openstates.sunlightlabs.com'
    n = 1
    s3_path = '%s-%02d-%02d-%s-csv.zip' % (today.year, today.month, today.day,
                                           state)
    s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)

    # S3 upload
    s3conn = boto.connect_s3(settings.AWS_KEY, settings.AWS_SECRET)
    bucket = s3conn.create_bucket(s3_bucket)
    k = Key(bucket)
    k.key = s3_path
    k.set_contents_from_filename(filename)
    k.set_acl('public-read')

    metadata = db.metadata.find_one({'_id': state})
    metadata['latest_csv_url'] = s3_url
    metadata['latest_csv_date'] = datetime.datetime.utcnow()
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
    parser.add_argument('--file', '-f',
                        help='filename to output to (defaults to <state>.zip)')
    parser.add_argument('--nodump', action='store_true', default=False,
                        help="don't run the dump, only upload")
    parser.add_argument('--upload', '-u', action='store_true', default=False,
                        help='upload the created archive to S3')

    args = parser.parse_args()

    settings.update(args)

    if not args.file:
        args.file = '{0}_csv.zip'.format(args.state)

    if not args.nodump:
        dump_csv(args.state, args.file)

    if args.upload:
        upload(args.state, args.file)
