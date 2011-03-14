import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.pa.utils import legislators_url

import lxml.html


class PALegislatorScraper(LegislatorScraper):
    state = 'pa'

    def scrape(self, chamber, term):
        # Pennsylvania doesn't make member lists easily available
        # for previous sessions, unfortunately
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        leg_list_url = legislators_url(chamber)

        with self.urlopen(leg_list_url) as page:
            page = lxml.html.fromstring(page)

            for link in page.xpath("//a[contains(@href, '_bio.cfm')]"):
                full_name = link.text[0:-4]
                district = re.search("District (\d+)", link.tail).group(1)

                party = link.text[-2]
                if party == 'R':
                    party = 'Republican'
                elif party == 'D':
                    party = 'Democratic'

                legislator = Legislator(term, chamber, district,
                                        full_name, party=party)
                legislator.add_source(leg_list_url)
                self.save_legislator(legislator)
