from openstates.scrape import Scraper, Organization

from .utils import MDBMixin


class NJCommitteeScraper(Scraper, MDBMixin):
    def scrape(self, session=None):
        if not session:
            session = self.jurisdiction.legislative_sessions[-1]["name"]
            self.info("no session specified, using %s", session)

        year_abr = session[0:4]

        self._init_mdb(year_abr)
        members_csv = self.access_to_csv("COMember")
        info_csv = self.access_to_csv("Committee")

        org_dictionary = {}

        # Committee Info Database
        for rec in info_csv:
            abrv = rec["Code"]
            comm_name = rec["Description"]

            if abrv[0] == "A":
                chamber = "lower"
            elif abrv[0] == "S":
                chamber = "upper"

            org = Organization(
                name=comm_name, chamber=chamber, classification="committee"
            )
            org.add_source("http://www.njleg.state.nj.us/downloads.asp")
            org_dictionary[abrv] = org

        # Committee Member Database
        POSITIONS = {"C": "chair", "V": "vice-chair", "": "member"}
        for member_rec in members_csv:
            # assignment=P means they are active, assignment=R means removed
            if member_rec["Assignment_to_Committee"] == "P":
                abr = member_rec["Code"]
                org = org_dictionary[abr]

                leg = member_rec["Member"]
                role = POSITIONS[member_rec["Position_on_Committee"]]
                leg = " ".join(leg.split(", ")[::-1])
                org.add_member(leg, role=role)

        for org in org_dictionary.values():
            yield org
