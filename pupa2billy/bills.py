from .utils import get_json, parse_psuedo_id, parse_date
from billy.scrape.bills import BillScraper, Bill


ACTION_MAPPING = {
    'introduction': 'bill:introduced',
    'passage': 'bill:passed',
    'failure': 'bill:failed',
    'withdrawal': 'bill:withdrawn',
    'substitution': 'bill:substituted',
    'filing': 'bill:filed',
    'veto-override-passage': 'bill:veto_override:passed',
    'veto-override-failure': 'bill:veto_override:failed',
    'executive-receipt': 'governor:received',
    'executive-signature': 'governor:signed',
    'executive-veto': 'governor:vetoed',
    'executive-veto-line-item': 'governor:vetoed:line-item',
    'amendment-introduction': 'amendment:introduced',
    'amendment-passage': 'amendment:passed',
    'amendment-failure': 'amendment:failed',
    'amendment-deferral': 'amendment:tabled',
    'amendment-amendment': 'amendment:amended',
    'amendment-withdrawal': 'amendment:withdrawn',
    'referral-committee': 'committee:referred',
    'committee-failure': 'committee:failed',
    'committee-passage': 'committee:passed',
    'committee-passage-favorable': 'committee:passed:favorable',
    'committee-passage-unfavorable': 'committee:passed:unfavorable',
    'reading-1': 'bill:reading:1',
    'reading-2': 'bill:reading:2',
    'reading-3': 'bill:reading:3',

    # obsolete
    'committee-referral': 'committee:referred',
}


def _action_categories(categories):
    return [ACTION_MAPPING[c] for c in categories if c != 'other']


class PupaBillScraper(BillScraper):

    def __init__(self, *args, **kwargs):
        self.jurisdiction = kwargs.pop('jurisdiction')
        super(PupaBillScraper, self).__init__(*args, **kwargs)

    def scrape(self, **kwargs):
        for bill in get_json(self.jurisdiction, 'bill'):
            self.process_bill(bill)

    def process_bill(self, data):
        chamber = parse_psuedo_id(data['from_organization'])['classification']
        if chamber == 'legislature':
            chamber = 'upper'
        bill = Bill(data['legislative_session'], chamber, data['identifier'],
                    data['title'], subjects=data['subject'],
                    type=data['classification'])
        if data['abstracts']:
            bill['summary'] = data['abstracts'][0]['abstract']
        bill.update(**data['extras'])

        for action in data['actions']:
            actor = parse_psuedo_id(action['organization_id'])['classification']
            legislators = []
            committees = []
            for rel in action['related_entities']:
                if rel['entity_type'] == 'organization':
                    committees.append(rel['name'])
                elif rel['entity_type'] == 'person':
                    legislators.append(rel['name'])
            bill.add_action(actor,
                            action['description'],
                            parse_date(action['date']),
                            type=_action_categories(action['classification']),
                            committees=committees,
                            legislators=legislators,
                            **action.get('extras', {})
                            )

        for source in data['sources']:
            bill.add_source(source['url'])

        for sponsor in data['sponsorships']:
            bill.add_sponsor(sponsor['classification'],
                             sponsor['name'],
                             )

        for version in data['versions']:
            for link in version['links']:
                bill.add_version(version['note'], link['url'],
                                 mimetype=link['media_type'],
                                 date=parse_date(version['date']),
                                 **version.get('extras', {}))

        for doc in data['documents']:
            for link in doc['links']:
                bill.add_document(doc['note'], link['url'],
                                  mimetype=link['media_type'],
                                  date=parse_date(doc['date']),
                                  **doc.get('extras', {}))

        for title in data['other_titles']:
            bill.add_title(title['title'])

        for related in data['related_bills']:
            bill.add_companion(related['identifier'],
                               related['legislative_session'],
                               chamber
                               )

        bill['alternate_bill_ids'] = [oi['identifier']  for oi in data['other_identifiers']]
        self.save_bill(bill)
