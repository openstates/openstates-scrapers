from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.ut import metadata

import lxml.html


class UTLegislatorScraper(LegislatorScraper):
    state = 'ut'

    def scrape(self, chamber, term):
        self.validate_term(term)

        if chamber == 'lower':
            title = 'Representative'
        else:
            title = 'Senator'

        url = 'http://www.le.state.ut.us/asp/roster/roster.asp?year=%s' % term

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for row in page.xpath('//table[2]/tr')[1:]:
                row_title = row.xpath('string(td[2])')

                if row_title == title:
                    full_name = row.xpath('string(td[1])')
                    district = row.xpath('string(td[4])')
                    party = row.xpath('string(td[3])')

                    leg = Legislator(term, chamber, district,
                                     full_name, '', '', '',
                                     party)
                    leg.add_source(url)
                    self.save_legislator(leg)
