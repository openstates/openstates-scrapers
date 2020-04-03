import logging

from openstates.scrape import Scraper, Organization
from .apiclient import OregonLegislatorODataClient
from .utils import SESSION_KEYS, index_legislators

logger = logging.getLogger("openstates")


class ORCommitteeScraper(Scraper):
    def scrape(self, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        if not session:
            session = self.latest_session()

        yield from self.scrape_committees(session)

    def scrape_committees(self, session):
        session_key = SESSION_KEYS[session]
        committees_response = self.api_client.get("committees", session=session_key)

        legislators = index_legislators(self, session_key)

        for committee in committees_response:
            org = Organization(
                chamber={"S": "upper", "H": "lower", "J": "legislature"}[
                    committee["HouseOfAction"]
                ],
                name=committee["CommitteeName"],
                classification="committee",
            )
            org.add_source(
                "https://olis.leg.state.or.us/liz/{session}"
                "/Committees/{committee}/Overview".format(
                    session=session_key, committee=committee["CommitteeName"]
                )
            )
            members_response = self.api_client.get(
                "committee_members",
                session=session_key,
                committee=committee["CommitteeCode"],
            )
            for member in members_response:
                try:
                    member_name = legislators[member["LegislatorCode"]]
                except KeyError:
                    logger.warn(
                        "Legislator {} not found in session {}".format(
                            member["LegislatorCode"], session_key
                        )
                    )
                    member_name = member["LegislatorCode"]
                org.add_member(
                    member_name, role=member["Title"] if member["Title"] else ""
                )

            yield org
