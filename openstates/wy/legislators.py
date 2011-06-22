import re

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class WYLegislatorScraper(LegislatorScraper):
    state = 'wy'

    def scrape(self, chamber, term):
        chamber_abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

        url = ("http://legisweb.state.wy.us/LegislatorSummary/LegislatorList"
               ".aspx?strHouse=%s&strStatus=N" % chamber_abbrev)
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'LegDetail')]"):
            name = link.text.strip()

            email_address = link.xpath("../../../td[2]//a")[0].attrib['href']
            email_address = email_address.split('Mailto:')[1]

            party = link.xpath("string(../../../td[3])").strip()
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'

            district = link.xpath(
                "string(../../../td[4])").strip().lstrip('HS0')

            leg = Legislator(term, chamber, district, name, party=party,
                             email_address=email_address)
            leg.add_source(url)
            self.save_legislator(leg)
