import os
import json
from .utils import get_json, parse_psuedo_id, parse_date
from billy.scrape.votes import VoteScraper, Vote
from . import settings


class PupaVoteScraper(VoteScraper):

    def get_bill_details(self, bill_uuid):
        if bill_uuid.startswith('~'):
            bill = parse_psuedo_id(bill_uuid)
            chamber = bill['from_organization__classification']
        else:
            bill = json.load(open(os.path.join(settings.PUPA_DATA_DIR,
                                               self.jurisdiction,
                                               'bill_' + bill_uuid + '.json')))
            chamber = parse_psuedo_id(bill['from_organization'])['classification']
        return chamber, bill['identifier']

    def __init__(self, *args, **kwargs):
        self.jurisdiction = kwargs.pop('jurisdiction')
        super(PupaVoteScraper, self).__init__(*args, **kwargs)

    def scrape(self, **kwargs):
        for vote in get_json(self.jurisdiction, 'vote_event'):
            self.process_vote(vote)

    def process_vote(self, data):
        chamber = parse_psuedo_id(data['organization'])['classification']
        bill_chamber, bill_id = self.get_bill_details(data['bill'])

        yes_count = None
        no_count = None
        other_count = 0
        for vc in data['counts']:
            if vc['option'] == 'yes':
                yes_count = vc['value']
            elif vc['option'] == 'no':
                no_count = vc['value']
            else:
                other_count += vc['value']

        vote = Vote(chamber=chamber,
                    date=parse_date(data['start_date']),
                    motion=data['motion_text'],
                    passed=data['result'] == 'pass',
                    yes_count=yes_count,
                    no_count=no_count,
                    other_count=other_count,
                    # TODO: was data['motion_classification'],
                    type='other',
                    session=data['legislative_session'],
                    bill_chamber=bill_chamber,
                    bill_id=bill_id,
                    )

        for vr in data['votes']:
            if vr['option'] == 'yes':
                vote.yes(vr['voter_name'])
            elif vr['option'] == 'no':
                vote.no(vr['voter_name'])
            else:
                vote.other(vr['voter_name'])

        for source in data['sources']:
            vote.add_source(source['url'])

        self.save_vote(vote)
