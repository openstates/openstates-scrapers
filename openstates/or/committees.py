import logging

from pupa.scrape import Scraper, Organization
from .apiclient import OregonLegislatorODataClient

logger = logging.getLogger('openstates')


class ORCommitteeScraper(Scraper):

    def scrape(self, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        self.session = session
        if not self.session:
            self.session = self.api_client.latest_session()

        yield from self.scrape_committee()

    def scrape_committee(self):
        committees_response = self.api_client.get('committees', session=self.session)

        legislators = self._index_legislators()

        for committee in committees_response:
            org = Organization(
                chamber={'S': 'upper', 'H': 'lower', 'J': 'joint'}[committee['HouseOfAction']],
                name=committee['CommitteeName'],
                classification='committee')
            org.add_source(
                'https://olis.leg.state.or.us/liz/{session}'
                '/Committees/{committee}/Overview'.format(session=self.session,
                                                          committee=committee['CommitteeName']))
            members_response = self.api_client.get('committee_members',
                                                   session=self.session,
                                                   committee=committee['CommitteeCode'])
            for member in members_response:
                try:
                    member_name = legislators[member['LegislatorCode']]
                except KeyError:
                    logger.warn('Legislator {} not found in session {}'.format(
                        member['LegislatorCode'], self.session))
                    member_name = member['LegislatorCode']
                org.add_member(member_name, role=member['Title'] if member['Title'] else '')

            yield org

    def _index_legislators(self):
        """
        Get the full name of legislators. The membership API only returns a "LegislatorCode".
        This will cross-reference the name.
        """
        legislators_response = self.api_client.get('legislators', session=self.session)

        legislators = {}
        for leg in legislators_response:
            legislators[leg['LegislatorCode']] = '{} {}'.format(leg['FirstName'], leg['LastName'])

        return legislators
