from pupa.scrape import Scraper, Organization
from .apiclient import OregonLegislatorODataClient


class ORCommitteeScraper(Scraper):
    def latest_session(self):
        self.session = self.api_client.get('sessions')[-1]['SessionKey']

    def scrape(self, chamber=None, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        self.session = session
        if not self.session:
            self.latest_session()

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
                    org.add_member(legislators[member['LegislatorCode']],
                                   role=member['Title'] if member['Title'] else '')
                except KeyError:
                    pass
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
