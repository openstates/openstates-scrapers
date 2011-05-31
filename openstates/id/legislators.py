import re

from billy.utils import urlescape
from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class IDLegislatorScraper(LegislatorScraper):
    state = 'id'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            chamber_name = 'senate'
        else:
            chamber_name = 'house'

        url = "http://legislature.idaho.gov/%s/membership.cfm" % chamber_name

        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for email_link in page.xpath("//a[contains(@href, 'contactmembers')]"):
            name = email_link.xpath("string(../../strong[1])").strip()
            name = name.replace(u'\xa0', ' ')
            name = re.sub(r'\s+', ' ', name)

            party = email_link.xpath("../../strong[1]")[0].tail.strip()
            if party == '(R)':
                party = 'Republican'
            elif party == '(D)':
                party = 'Democratic'

            text = email_link.xpath("string(../..)")
            try:
                district = re.search(r'District (\d+)', text).group(1)
            except AttributeError:
                continue

            photo_url = email_link.xpath("../../../td/img")[0].attrib['src']

            leg = Legislator(term, chamber, district, name, party=party,
                             photo_url=photo_url)
            leg.add_source(url)
            self.save_legislator(leg)
