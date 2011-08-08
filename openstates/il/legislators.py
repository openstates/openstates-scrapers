# -*- coding: utf-8 -*-
import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator

MEMBER_LIST_URL = {
    'upper': 'http://ilga.gov/senate/default.asp?GA=%s',
    'lower': 'http://ilga.gov/house/default.asp?GA=%s',
}


class ILLegislatorScraper(LegislatorScraper):
    state = 'il'

    def scrape(self, chamber, term):
        term_slug = term[:-2]
        url = MEMBER_LIST_URL[chamber] % term_slug

        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for row in doc.xpath('//table')[4].xpath('tr')[2:]:
            name, _, _, district, party = row.xpath('td')
            district = district.text
            party = {'D':'Democratic', 'R': 'Republican'}[party.text]
            leg_url = name.xpath('a/@href')[0]
            name = name.text_content().strip()

            # inactive legislator, skip them for now
            if name.endswith('*'):
                continue

            leg = Legislator(term, chamber, district, name, party=party)
            leg.add_source(url)
            leg.add_source(leg_url)
            self.save_legislator(leg)
