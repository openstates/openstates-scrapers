from .utils import xpath
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.etree


class WACommitteeScraper(CommitteeScraper):
    jurisdiction = 'wa'

    _base_url = 'http://wslwebservices.leg.wa.gov/CommitteeService.asmx'

    def scrape(self, chamber, term):
        biennium = "%s-%s" % (term[0:4], term[7:9])

        url = "%s/GetActiveCommittees?biennium=%s" % (self._base_url, biennium)
        page = self.get(url)
        page = lxml.etree.fromstring(page.content)

        for comm in xpath(page, "//wa:Committee"):
            agency = xpath(comm, "string(wa:Agency)")
            comm_chamber = {'House': 'lower', 'Senate': 'upper'}[agency]
            if comm_chamber != chamber:
                continue

            name = xpath(comm, "string(wa:Name)")
            comm_id = xpath(comm, "string(wa:Id)")
            # acronym = xpath(comm, "string(wa:Acronym)")
            phone = xpath(comm, "string(wa:Phone)")

            comm = Committee(chamber, name, _code=comm_id,
                             office_phone=phone)
            self.scrape_members(comm, agency)
            comm.add_source(url)
            if comm['members']:
                self.save_committee(comm)

    def scrape_members(self, comm, agency):
        # Can't get them to accept special characters (e.g. &) in URLs,
        # no matter how they're encoded, so we use the SOAP API here.
        template = """
        <?xml version="1.0" encoding="utf-8"?>
        <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
          <soap12:Body>
            <GetActiveCommitteeMembers xmlns="http://WSLWebServices.leg.wa.gov/">
              <agency>%s</agency>
              <committeeName>%s</committeeName>
            </GetActiveCommitteeMembers>
          </soap12:Body>
        </soap12:Envelope>
        """.strip()

        body = template % (agency, comm['committee'].replace('&', '&amp;'))
        headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}
        resp = self.post(self._base_url, data=body, headers=headers)
        doc = lxml.etree.fromstring(resp.content)

        if 'subcommittee' in comm['committee'].lower():
            roles = ['chair', 'ranking minority member']
        else:
            roles = ['chair', 'vice chair', 'ranking minority member',
                     'assistant ranking minority member']

        for i, member in enumerate(xpath(doc, "//wa:Member")):
            name = xpath(member, "string(wa:Name)")
            try:
                role = roles[i]
            except IndexError:
                role = 'member'
            comm.add_member(name, role)
