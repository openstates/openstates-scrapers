from .utils import xpath
from openstates.scrape import Scraper, Organization

import lxml.etree


class WACommitteeScraper(Scraper):

    _base_url = "http://wslwebservices.leg.wa.gov/CommitteeService.asmx"

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):

        url = "%s/GetActiveCommittees?biennium=%s" % (self._base_url, session)
        page = self.get(url)
        page = lxml.etree.fromstring(page.content)

        for comm in xpath(page, "//wa:Committee"):
            agency = xpath(comm, "string(wa:Agency)")
            comm_chamber = {"House": "lower", "Senate": "upper"}[agency]
            if comm_chamber != chamber:
                continue

            name = xpath(comm, "string(wa:Name)")
            # comm_id = xpath(comm, "string(wa:Id)")
            # acronym = xpath(comm, "string(wa:Acronym)")
            phone = xpath(comm, "string(wa:Phone)")

            comm = Organization(name, chamber=chamber, classification="committee")
            comm.extras["phone"] = phone
            self.scrape_members(comm, agency)
            comm.add_source(url)
            if not comm._related:
                self.warning("empty committee: %s", name)
            else:
                yield comm

    def scrape_members(self, comm, agency):
        # Can't get them to accept special characters (e.g. &) in URLs,
        # no matter how they're encoded, so we use the SOAP API here.
        template = """
        <?xml version="1.0" encoding="utf-8"?>
        <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
          <soap12:Body>
            <GetActiveCommitteeMembers xmlns="http://WSLWebServices.leg.wa.gov/">
              <agency>%s</agency>
              <committeeName>%s</committeeName>
            </GetActiveCommitteeMembers>
          </soap12:Body>
        </soap12:Envelope>
        """.strip()

        body = template % (agency, comm.name.replace("&", "&amp;"))
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
        resp = self.post(self._base_url, data=body, headers=headers)
        doc = lxml.etree.fromstring(resp.content)

        if "subcommittee" in comm.name.lower():
            roles = ["chair", "ranking minority member"]
        else:
            roles = [
                "chair",
                "vice chair",
                "ranking minority member",
                "assistant ranking minority member",
            ]

        for i, member in enumerate(xpath(doc, "//wa:Member")):
            name = xpath(member, "string(wa:Name)")
            try:
                role = roles[i]
            except IndexError:
                role = "member"
            comm.add_member(name, role)
