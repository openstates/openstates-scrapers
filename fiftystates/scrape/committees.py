from __future__ import with_statement
import os

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates.scrape import Scraper, FiftystatesObject, JSONDateEncoder


class CommitteeScraper(Scraper):
    def scrape(self, chamber, year):
        raise NotImplementedError('CommitteeScrapers must define a '
                                  'scrape method')

    def save_committee(self, committee):
        """
        Save a scraped :class:`pyutils.legislation.Committee` object.
        Only call after all data for the given committeee has been collected.
        """
        self.log("save_committeee: %s" % committee['name'])

        filename = "%(chamber)s_%(name)s.json" % committee

        with open(os.path.join(self.output_dir, "committees", filename),
                  'w') as f:
            json.dump(committee, f, cls=JSONDateEncoder)


class Committee(FiftystatesObject):
    def __init__(self, chamber, name, parent=None, **kwargs):
        super(Committee, self).__init__('committee', **kwargs)
        self['chamber'] = chamber
        self['name'] = name
        self['members'] = []

    def add_member(self, legislator, role='member', **kwargs):
        self['members'].append(dict(legislator=legislator, role=role,
                                    **kwargs))
