import json
import re

from billy.scrape.committees import Committee, CommitteeScraper


class VTCommitteeScraper(CommitteeScraper):
    jurisdiction = 'vt'
    latest_only = True

    def scrape(self, session, chambers):
        year_slug = session[5: ]

        # Load all committees via the private API
        committee_dump_url = \
                'http://legislature.vermont.gov/committee/loadList/{}/'.\
                format(year_slug)
        json_data = self.get(committee_dump_url).text
        committees = json.loads(json_data)['data']

        # Parse the information from each committee
        for info in committees:
            # Strip whitespace from strings
            info = { k:v.strip() for k, v in info.iteritems() }

            # Determine the chamber
            if info['CommitteeType'] == 'House Standing':
                chamber = 'lower'
            elif info['CommitteeType'] == 'Senate Standing':
                chamber = 'upper'
            elif info['CommitteeType'] == 'Joint Committee':
                chamber = 'joint'
            elif info['CommitteeType'] in ('Study Committee', 'Commissions'):
                if info['CommitteeName'].startswith("House"):
                    chamber = 'lower'
                elif info['CommitteeName'].startswith("Senate"):
                    chamber = 'upper'
                else:
                    chamber = 'joint'
            else:
                raise AssertionError(
                        "Unknown committee type found: '{}'".
                        format(info['CommitteeType'])
                        )
            comm = Committee(
                    chamber=chamber,
                    committee=info['CommitteeName']
                    )

            # Determine membership and member roles
            # First, parse the member list and make sure it isn't a placeholder
            REMOVE_TAGS_RE = r'<.*?>'
            members = [
                    re.sub(REMOVE_TAGS_RE, '', x)
                    for x
                    in info['Members'].split('</br>')
                    ]
            members = [x.strip() for x in members if x.strip()]

            for member in members:
                # Strip out titles, and exclude committee assistants
                if member.startswith("Rep. "):
                    member = member[len("Rep. "): ]
                elif member.startswith("Sen. "):
                    member = member[len("Sen. "): ]
                else:
                    self.info("Non-legislator member found: {}".format(member))

                # Determine the member's role in the committee
                if ',' in member:
                    (member, role) = [x.strip() for x in member.split(',')]
                    if 'jr' in role.lower() or 'sr' in role.lower():
                        raise AssertionError(
                                "Name suffix confused for a committee role")
                else:
                    role = 'member'

                comm.add_member(
                        legislator=member,
                        role=role
                        )

            comm.add_source(committee_dump_url)

            self.save_committee(comm)
