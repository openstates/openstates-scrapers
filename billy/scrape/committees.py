import os
import json

from billy.scrape import Scraper, SourcedObject, JSONDateEncoder


class CommitteeScraper(Scraper):

    scraper_type = 'committees'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/committee.json')
        schema = json.load(open(schema_path))
        return schema

    def scrape(self, chamber, term):
        raise NotImplementedError('CommitteeScrapers must define a '
                                  'scrape method')

    def save_committee(self, committee):
        """
        Save a scraped :class:`~billy.scrape.committees.Committee` object.
        """
        name = committee['committee']
        if committee.get('subcommittee', None):
            name += '_%s' % committee['subcommittee']
        self.log("save_committee: %s" % name)
        self.save_object(committee)


class Committee(SourcedObject):
    def __init__(self, chamber, committee, subcommittee=None,
                 **kwargs):
        """
        Create a Committee.

        :param chamber: the chamber this committee is associated with ('upper',
            'lower', or 'joint')
        :param committee: the name of the committee
        :param subcommittee: the name of the subcommittee (optional)
        """
        super(Committee, self).__init__('committee', **kwargs)
        self['chamber'] = chamber
        self['committee'] = committee
        self['subcommittee'] = subcommittee
        self['members'] = kwargs.get('members', [])

    def add_member(self, legislator, role='member', **kwargs):
        """
        Add a member to the committee object.

        :param legislator: name of the legislator
        :param role: role that legislator holds in the committee
            (eg. chairman) default: 'member'
        """
        self['members'].append(dict(name=legislator, role=role,
                                    **kwargs))

    def get_filename(self):
        name = self['committee']
        if self.get('subcommittee', None):
            name += '_%s' % self['subcommittee']

        return "%s_%s.json" % (self['chamber'], name.replace('/', ','))

