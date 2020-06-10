from openstates.scrape import Scraper, Organization
from .client import AZClient
from . import session_metadata


class AZCommitteeScraper(Scraper):
    jurisdiction = "az"

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            chambers = ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        session = self.latest_session()
        # since we are scraping only latest_session
        session_id = session_metadata.session_id_meta_data[session]

        client = AZClient()
        committees = client.list_committees(
            sessionId=session_id,
            includeOnlyCommitteesWithAgendas="false",
            legislativeBody="S" if chamber == "upper" else "H",
        )
        for committee in committees.json():
            c = Organization(
                name=committee["CommitteeName"],
                chamber=chamber,
                classification="committee",
            )
            details = client.get_standing_committee(
                sessionId=session_id,
                legislativeBody="S" if chamber == "upper" else "H",
                committeeId=committee["CommitteeId"],
                includeMembers="true",
            )
            for member in details.json()[0]["Members"]:
                c.add_member(
                    u"{} {}".format(member["FirstName"], member["LastName"]),
                    role=parse_role(member),
                )
                c.add_source(details.url)

            c.add_source(committees.url)
            yield c


def parse_role(member):
    if member["IsChair"]:
        return "chair"
    if member["IsViceChair"]:
        return "vice chair"
    return "member"
