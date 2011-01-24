import urllib

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.etree


class WACommitteeScraper(CommitteeScraper):
    state = 'wa'

    _base_url = 'http://wslwebservices.leg.wa.gov/CommitteeService.asmx'
    _ns = {'wa': "http://WSLWebServices.leg.wa.gov/"}

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

            for comm in page.xpath("//wa:Committee", namespaces=self._ns):
                agency = comm.xpath("string(wa:Agency)", namespaces=self._ns)
                comm_chamber = {'House': 'lower', 'Senate': 'upper'}[agency]
                if comm_chamber != chamber:
                    continue

                name = comm.xpath("string(wa:Name)", namespaces=self._ns)
                comm_id = comm.xpath("string(wa:Id)", namespaces=self._ns)
                acronym = comm.xpath("string(wa:Acronym)",
                                     namespaces=self._ns)
                phone = comm.xpath("string(wa:Phone)", namespaces=self._ns)

                comm = Committee(chamber, name)
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

            for member in page.xpath("//wa:Member", namespaces=self._ns):
                name = member.xpath("string(wa:Name)", namespaces=self._ns)
                comm.add_member(name)
