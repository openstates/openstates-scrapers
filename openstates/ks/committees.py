import scrapelib
from billy.scrape.committees import Committee, CommitteeScraper

import ksapi
from throttle import ThrottleWrapper


class KSCommitteeScraper(CommitteeScraper):
    jurisdiction = 'ks'
    latest_only = True

    def scrape(self, chamber, term):
        # some committees, 500, let them go
        self.retry_attempts = 0

        self.throttle = ThrottleWrapper(self)

        self.scrape_current(chamber, term)

    def scrape_current(self, chamber, term):
        attempts = 1
        max_attempts = 5
        if chamber == 'upper':
            chambers = ['special_committees', 'senate_committees']
        else:
            chambers = ['house_committees']

        committee_json = self.throttle.get(ksapi.url + 'ctte/', attempts=attempts, max_attempts=max_attempts)

        for com_type in chambers:
            committees = committee_json['content'][com_type]

            for committee_data in committees:

                # set to joint if we are using the special_committees
                com_chamber = ('joint' if com_type == 'special_committees'
                               else chamber)

                committee = Committee(com_chamber, committee_data['TITLE'])

                com_url = ksapi.url + 'ctte/%s/' % committee_data['KPID']

                try:
                    detail_json = self.throttle.get(com_url, attempts=attempts, max_attempts=max_attempts)
                except scrapelib.HTTPError:
                    self.warning("error fetching committee %s" % com_url)
                    continue
                    
                details = detail_json['content']
                for chair in details['CHAIR']:
                    if chair.get('FULLNAME', None):
                        chair_name = chair['FULLNAME']
                    else:
                        chair_name = self.parse_kpid(chair['KPID'])
                        self.warning('no FULLNAME for %s', chair['KPID'])
                    committee.add_member(chair_name, 'chairman')
                for vicechair in details['VICECHAIR']:
                    committee.add_member(vicechair['FULLNAME'], 'vice-chairman')
                for rankedmember in details['RMMEM']:
                    committee.add_member(rankedmember['FULLNAME'], 'ranking member')
                for member in details['MEMBERS']:
                    committee.add_member(member['FULLNAME'])

                if not committee['members']:
                    self.warning('skipping blank committee %s' %
                                 committee_data['TITLE'])
                else:
                    committee.add_source(com_url)
                    self.save_committee(committee)

    def parse_kpid(self, kpid):
        """
        Helper function to parse KPID given in data when FULLNAME is not available.

        :param kpid: str, pre_formatted identifier in the format type_family_given_number
        :return: str, formatted Fullname from id
        """
        kpid_parts = kpid.split('_')
        return ' '.join(reversed(kpid_parts[1:-1])).title()
