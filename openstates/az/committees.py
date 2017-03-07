import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

from .client import AZClient


class AZCommitteeScraper(CommitteeScraper):
    jurisdiction = 'az'

    def get_session_for_term(self, term):
        # ideally this should be either first or second regular session
        # and probably first and second when applicable
        for t in self.metadata['terms']:
            if t['name'] == term:
                session = t['sessions'][-1]
                if re.search('regular', session):
                    return session
                else:
                    return t['sessions'][0]

    def get_session_id(self, session):
        return self.metadata['session_details'][session]['session_id']

    def scrape(self, chamber, term):
        self.validate_term(term)
        session = self.get_session_for_term(term)
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod

        client = AZClient()
        committees = client.list_committees(
            sessionId=session_id,
            includeOnlyCommitteesWithAgendas='false',
            legislativeBody='S' if chamber == 'upper' else 'H',
        )
        for committee in committees.json():
            c = Committee(
                chamber,
                committee['CommitteeName'],
                session=session,
                az_committee_id=committee['CommitteeId'],
            )

            details = client.get_standing_committee(
                sessionId=session_id,
                legislativeBody='S' if chamber == 'upper' else 'H',
                committeeId=committee['CommitteeId'],
                includeMembers='true',
            )
            for member in details.json()[0]['Members']:
                c.add_member(
                    u'{} {}'.format(member['FirstName'], member['LastName']),
                    role=parse_role(member),
                )
                c.add_source(details.url)

            c.add_source(committees.url)
            self.save_committee(c)


def parse_role(member):
    if member['IsChair']:
        return 'chair'
    if member['IsViceChair']:
        return 'vice chair'
    return 'member'
