import re

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class INLegislatorScraper(LegislatorScraper):
    state = 'in'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        chamber_name = {'upper': 'Senate',
                        'lower': 'House'}[chamber]

        url = ("http://www.in.gov/cgi-bin/legislative/listing/"
               "listing-2.pl?data=alpha&chamber=%s" % chamber_name)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for link in page.xpath("//div[@id='col2']/p/a"):
                name = link.text.strip()
                href = link.get('href')

                details = link.getnext().text.strip()

                party = details.split(',')[0]
                if party == 'Democrat':
                    party = 'Democratic'

                district = re.search(r'District (\d+)', details).group(1)
                district = district.lstrip('0')

                leg = Legislator(term, chamber, district, name, party=party,
                                 url=href)
                leg.add_source(url)

                self.save_legislator(leg)
