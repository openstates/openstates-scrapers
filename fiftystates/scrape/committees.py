from __future__ import with_statement
import os

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates.scrape import Scraper, FiftystatesObject, JSONDateEncoder


class CommitteeScraper(Scraper):

    scraper_type = 'committees'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../../schemas/committee.json')
        schema = json.load(open(schema_path))
        return schema

    def scrape(self, chamber, year):
        raise NotImplementedError('CommitteeScrapers must define a '
                                  'scrape method')

    def save_committee(self, committee):
        """
        Save a scraped :class:`~fiftystates.scrape.committees.Committee` object.
        Only call after all data for the given committee has been collected.
        """
        name = committee['committee']
        if 'subcommittee' in committee:
            name += '_%s' % committee['subcommittee']
        self.log("save_committee: %s" % name)

        committee['state'] = self.state

        self.validate_json(committee)

        filename = "%s_%s.json" % (committee['chamber'],
                                   name.replace('/', ','))

        with open(os.path.join(self.output_dir, "committees", filename),
                  'w') as f:
            json.dump(committee, f, cls=JSONDateEncoder)


class Committee(FiftystatesObject):
    def __init__(self, chamber, committee, subcommittee=None,
                 **kwargs):
        super(Committee, self).__init__('committee', **kwargs)
        self['chamber'] = chamber
        self['committee'] = committee
        self['subcommittee'] = subcommittee
        self['members'] = kwargs.get('members', [])

    def add_member(self, legislator, role='member', **kwargs):
        self['members'].append(dict(name=legislator, role=role,
                                    **kwargs))
