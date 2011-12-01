import re
import os
import datetime
import json

from billy.scrape.committees import Committee, CommitteeScraper
from billy.scrape import NoDataForPeriod

import ksapi

class KSBillScraper(CommitteeScraper):
    state = 'ks'

    def scrape(self, chamber, term):
        # older terms are accessible but through an archived site
        self.validate_term(term, latest_only=True)

        self.scrape_current(chamber, term)

    def scrape_current(self, chamber, term):
        for committee_type in ['special', 'senate' if chamber == 'upper' else 'lower']:
            with self.urlopen(ksapi.url + 'ctte/') as committee_request:
                committee_json = json.loads(committee_request)
                if 'content' not in committee_json or '%s_committees' % committee_type not in committee_json['content']:
                    continue

                committees = committee_json['content']['%s_committees' % committee_type]

                for committee_data in committees:
                    committee = Committee(chamber, committee_data['TITLE'])
                    if committee_data['KPID'] in ksapi.bad_committees:
                        continue
                    with self.urlopen(ksapi.url + 'ctte/%s/' % committee_data['KPID']) as committee_details_request:
                        committee_details_json = json.loads(committee_details_request)
                        if 'content' not in committee_details_json:
                            continue
                        committee_details = committee_details_json['content']
                        for chair in committee_details['CHAIR']:
                            committee.add_member(chair['FULLNAME'], 'chairman')
                        for vicechair in committee_details['VICECHAIR']:
                            committee.add_member(vicechair['FULLNAME'], 'vice-chairman')
                        for rankedmember in committee_details['RMMEM']:
                            committee.add_member(rankedmember['FULLNAME'], 'ranking member')
                        for member in committee_details['MEMBERS']:
                            committee.add_member(member['FULLNAME'])
                    self.save_committee(committee)

