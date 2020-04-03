import json

from openstates_core.scrape import Scraper, Organization


class WYCommitteeScraper(Scraper):
    def scrape(self, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        # com_types = ['J', 'SE', 'O']
        # base_url = 'https://wyoleg.gov/LsoService/api/committeeList/2018/J'
        url = "https://wyoleg.gov/LsoService/api/committees/{}".format(session)

        response = self.get(url)
        coms_json = json.loads(response.content.decode("utf-8"))

        for row in coms_json:
            com_url = "https://wyoleg.gov/LsoService/api/committeeDetail/{}/{}".format(
                session, row["ownerID"]
            )
            com_response = self.get(com_url)
            com = json.loads(com_response.content.decode("utf-8"))

            # WY doesn't seem to have any house/senate only committees that I can find
            committee = Organization(
                name=com["commName"], chamber="legislature", classification="committee"
            )

            for member in com["commMembers"]:
                role = "chairman" if member["chairman"] == "Chairman" else "member"
                committee.add_member(member["name"], role)

            # some WY committees have non-legislators appointed to the member by the Governor
            # but the formatting is super inconsistent
            if com["otherMembers"]:
                committee.extras["other_members"] = com["otherMembers"]

            committee.extras["wy_id"] = com["commID"]
            committee.extras["wy_code"] = com["ownerID"]
            committee.extras["wy_type_code"] = com["type"]
            committee.extras["budget"] = com["budget"]

            if com["statAuthority"]:
                committee.extras["statutory_authority"] = com["statAuthority"]

            if com["number"]:
                committee.extras["seat_distribution"] = com["number"]

            committee.add_identifier(
                scheme="WY Committee ID", identifier=str(com["commID"])
            )
            committee.add_identifier(
                scheme="WY Committee Code", identifier=str(com["ownerID"])
            )

            if com["description"]:
                committee.add_identifier(
                    scheme="Common Name", identifier=com["description"]
                )

            source_url = "http://wyoleg.gov/Committees/{}/{}".format(
                session, com["ownerID"]
            )
            committee.add_source(source_url)

            yield committee
