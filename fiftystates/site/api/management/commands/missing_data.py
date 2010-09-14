import csv
from fiftystates.backend import db

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open('committee_votesmart_ids.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["State", "Chamber", "Committee Name",
                             "Subcommittee Name", "OSP ID", "Votesmart ID"])

            if args:
                query = {'state': {'$in': args}}
            else:
                query = {}

            for committee in db.committees.find(query):
                if committee.get('votesmart_id'):
                    continue

                writer.writerow([
                    committee['state'],
                    committee['chamber'],
                    committee['committee'].encode('ascii', 'replace'),
                    commitee.get('subcommittee', '').encode(
                        'ascii', 'replace'),
                    committee['_id'],
                    ""])
