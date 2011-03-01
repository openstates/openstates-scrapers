import urllib

from .utils import xpath
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.etree


class WACommitteeScraper(CommitteeScraper):
    state = 'wa'

    _base_url = 'http://wslwebservices.leg.wa.gov/CommitteeService.asmx'

    def _make_headers(self, url):
        headers = super(WACommitteeScraper, self)._make_headers(url)
        if url == self._base_url:
            headers['Content-Type'] = 'application/soap+xml; charset=utf-8'
        return headers

    def scrape(self, chamber, term):
        biennium = "%s-%s" % (term[0:4], term[7:9])

        url = "%s/GetActiveCommittees?biennium=%s" % (self._base_url, biennium)
        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page)

            for comm in xpath(page, "//wa:Committee"):
                agency = xpath(comm, "string(wa:Agency)")
                comm_chamber = {'House': 'lower', 'Senate': 'upper'}[agency]
                if comm_chamber != chamber:
                    continue

                name = xpath(comm, "string(wa:Name)")
                comm_id = xpath(comm, "string(wa:Id)")
                acronym = xpath(comm, "string(wa:Acronym)")
                phone = xpath(comm, "string(wa:Phone)")

                comm = Committee(chamber, name, _code=comm_id,
                                 office_phone=phone)
                self.scrape_members(comm, agency)
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
        with self.urlopen(self._base_url, method='POST', body=body) as page:
            page = lxml.etree.fromstring(page)

            for member in xpath(page, "//wa:Member"):
                name = xpath(member, "string(wa:Name)")
                comm.add_member(name)
