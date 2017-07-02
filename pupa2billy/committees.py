from collections import defaultdict
from billy.scrape.committees import CommitteeScraper, Committee
from .utils import get_json, parse_psuedo_id


class PupaCommitteeScraper(CommitteeScraper):

    def __init__(self, *args, **kwargs):
        self.jurisdiction = kwargs.pop('jurisdiction')
        super(PupaCommitteeScraper, self).__init__(*args, **kwargs)

    def scrape(self, **kwargs):
        self.memberships = defaultdict(list)

        for mem in get_json(self.jurisdiction, 'membership'):
            self.memberships[mem['organization_id']].append(mem)

        for com in get_json(self.jurisdiction, 'organization'):
            self.process_committee(com)

    def process_committee(self, data):
        if data['classification'] != 'committee':
            return

        parent = parse_psuedo_id(data['parent_id'])
        if not parent:
            return
        chamber = parent['classification']

        if chamber == 'legislature':
            chamber = 'upper'

        if 'name' in parent:
            com = Committee(chamber, parent['name'], subcommittee=data['name'])
        else:
            com = Committee(chamber, data['name'])

        for member in self.memberships[data['_id']]:
            com.add_member(member['person_name'], role=member['role'], **member.get('extras', {}))

        for source in data['sources']:
            com.add_source(source['url'])

        com.update(**data['extras'])

        self.save_committee(com)
