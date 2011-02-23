import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html

class ARLegislatorScraper(LegislatorScraper):
    state = 'ar'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod

        url = ('http://www.arkleg.state.ar.us/assembly/2011/2011R/Pages/'
               'LegislatorSearchResults.aspx?member=&committee=All&chamber=')

        with self.urlopen(url) as page:
            root = lxml.html.fromstring(page)

            for a in root.xpath('//table[@class="dxgvTable"] \
                                  /tr[contains(@class, "dxgvDataRow")] \
                                  /td[1] \
                                  /a'):
                member_url = a.attrib['href']
                print member_url

    def scrape_member(self, chamber, term, member_url):
        pass
