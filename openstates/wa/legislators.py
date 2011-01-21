import datetime

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.etree


class WALegislatorScraper(LegislatorScraper):
    state = 'wa'

    _ns = {'wa': "http://WSLWebServices.leg.wa.gov/"}

    def scrape(self, chamber, term):
        biennium = "%s-%s" % (term[0:4], term[7:9])

        url = ("http://wslwebservices.leg.wa.gov/SponsorService.asmx/"
               "GetSponsors?biennium=%s" % biennium)
        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page)

            for member in page.xpath("//wa:Member", namespaces=self._ns):
                mchamber = member.xpath("string(wa:Agency)",
                                       namespaces=self._ns)
                mchamber = {'House': 'lower', 'Senate': 'upper'}[mchamber]

                if mchamber != chamber:
                    continue

                name = member.xpath("string(wa:Name)", namespaces=self._ns)

                party = member.xpath("string(wa:Party)", namespaces=self._ns)
                party = {'R': 'Republican', 'D': 'Democratic'}.get(
                    party, party)

                district = member.xpath("string(wa:District)",
                                        namespaces=self._ns)
                email = member.xpath("string(wa:Email)",
                                     namespaces=self._ns)
                leg_id = member.xpath("string(wa:Id)", namespaces=self._ns)
                phone = member.xpath("string(wa:Phone)", namespaces=self._ns)

                leg = Legislator(term, chamber, district,
                                 name, '', '', '', party, email=email,
                                 _code=leg_id, office_phone=phone)

                self.save_legislator(leg)
