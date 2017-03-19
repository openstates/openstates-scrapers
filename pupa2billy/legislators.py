from collections import defaultdict

from .utils import get_json, parse_psuedo_id
from billy.scrape.legislators import LegislatorScraper, Legislator


class PupaLegislatorScraper(LegislatorScraper):

    def __init__(self, *args, **kwargs):
        self.jurisdiction = kwargs.pop('jurisdiction')
        super(PupaLegislatorScraper, self).__init__(*args, **kwargs)

    def scrape(self, **kwargs):
        self._load_orgs()
        self._load_memberships()
        for person in get_json(self.jurisdiction, 'person'):
            self.process_person(person)

    def _load_orgs(self):
        # org_id -> org
        self.organizations = defaultdict(list)
        for org in get_json(self.jurisdiction, 'organization'):
            self.organizations[org['_id']] = org

    def _load_memberships(self):
        # person_id -> {org: org, post: post}
        self.memberships = defaultdict(list)

        for membership in get_json(self.jurisdiction, 'membership'):
            org = self.organizations.get(membership['organization_id'])
            if not org:
                org = parse_psuedo_id(membership['organization_id'])
            post = parse_psuedo_id(membership['post_id'])

            self.memberships[membership['person_id']].append({
                'org': org,
                'post': post,
            })

    def process_person(self, person):
        term = self.metadata['terms'][-1]['name']
        chamber = None
        district = None
        party = None
        name = person['name']
        url = person['links'][0]['url']
        photo_url = person['image']

        for membership in self.memberships[person['_id']]:
            org = membership['org']
            post = membership['post']
            if not org:
                print(membership)
            classification = org.get('classification') or org.get('organization__classification')
            if classification in ('upper', 'lower'):
                chamber = classification
                district = post['label']
            elif classification == 'party':
                party = org['name']

        district_office = {}
        capitol_office = {}
        email = ''
        for detail in person['contact_details']:
            # rename voice->phone
            if detail['type'] == 'voice':
                detail['type'] = 'phone'
            elif detail['type'] == 'email':
                email = detail['value']
            if 'district' in detail['note'].lower():
                district_office[detail['type']] = detail['value']
            elif 'capitol' in detail['note'].lower():
                capitol_office[detail['type']] = detail['value']

        leg = Legislator(term, chamber, district, name,
                         party=party, url=url,
                         photo_url=photo_url,
                         email=email
                         )

        if district_office:
            leg.add_office('district', 'District Office', **district_office)
        if capitol_office:
            leg.add_office('capitol', 'Capitol Office', **capitol_office)

        for source in person['sources']:
            leg.add_source(source['url'])

        self.save_legislator(leg)
