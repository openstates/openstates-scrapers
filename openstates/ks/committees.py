import re
import os
import datetime
import json

from billy.scrape.committees import Committee, CommitteeScraper

import ksapi

class KSBillScraper(CommitteeScraper):
    state = 'ks'

    def scrape(self, chamber, term):
        # older terms are accessible but through an archived site
        self.validate_term(term, latest_only=True)

        self.scrape_current(chamber, term)

    def scrape_current(self, chamber, term):
        if chamber == 'upper':
            chambers = ['special_committees', 'senate_committees']
        else:
            chambers = ['house_committees']

        with self.urlopen(ksapi.url + 'ctte/') as committee_request:
            committee_json = json.loads(committee_request)

            for com_type in chambers:
                committees = committee_json['content'][com_type]

                for committee_data in committees:

                    # set to joint if we are using the special_committees
                    com_chamber = ('joint' if com_type == 'special_committees'
                                   else chamber)

                    committee = Committee(com_chamber, committee_data['TITLE'])

                    # some committee URLs are broken
                    if committee_data['KPID'] in ksapi.bad_committees:
                        continue

                    with self.urlopen(ksapi.url + 'ctte/%s/' %
                                      committee_data['KPID']) as detail_json:
                        details = json.loads(detail_json)['content']
                        for chair in details['CHAIR']:
                            committee.add_member(chair['FULLNAME'], 'chairman')
                        for vicechair in details['VICECHAIR']:
                            committee.add_member(vicechair['FULLNAME'], 'vice-chairman')
                        for rankedmember in details['RMMEM']:
                            committee.add_member(rankedmember['FULLNAME'], 'ranking member')
                        for member in details['MEMBERS']:
                            committee.add_member(member['FULLNAME'])
                    self.save_committee(committee)
