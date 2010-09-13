import csv
from fiftystates.backend import db

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open('committee_votesmart_ids.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["State", "Chamber", "Committee Name",
                             "Subcommittee Name", "OSP ID", "Votesmart ID"])
            for committee in db.committees.find():
                if committee.get('votesmart_id'):
                    continue

                writer.writerow([committee['state'],
                                 committee['chamber'],
                                 committee['committee'],
                                 committee['subcommittee'],
                                 committee['_id'],
                                 ""])
