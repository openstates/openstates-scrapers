import datetime

from .utils import xpath
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.etree


class WALegislatorScraper(LegislatorScraper):
    state = 'wa'

    def scrape(self, chamber, term):
        biennium = "%s-%s" % (term[0:4], term[7:9])

        url = ("http://wslwebservices.leg.wa.gov/SponsorService.asmx/"
               "GetSponsors?biennium=%s" % biennium)
        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page)

            for member in xpath(page, "//wa:Member"):
                mchamber = xpath(member, "string(wa:Agency)")
                mchamber = {'House': 'lower', 'Senate': 'upper'}[mchamber]

                if mchamber != chamber:
                    continue

                name = xpath(member, "string(wa:Name)")
                party = xpath(member, "string(wa:Party)")
                party = {'R': 'Republican', 'D': 'Democratic'}.get(
                    party, party)

                district = xpath(member, "string(wa:District)")
                email = xpath(member, "string(wa:Email)")
                leg_id = xpath(member, "string(wa:Id)")
                phone = xpath(member, "string(wa:Phone)")

                leg = Legislator(term, chamber, district,
                                 name, '', '', '', party, email=email,
                                 _code=leg_id, office_phone=phone)

                self.save_legislator(leg)
