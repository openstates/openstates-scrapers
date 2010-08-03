import re
import datetime

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class AKLegislatorScraper(LegislatorScraper):
    state = 'ak'

    def scrape(self, chamber, term):
        if chamber == 'upper':
            chamber_abbr = 'S'
        else:
            chamber_abbr = 'H'

        url = ("http://www.legis.state.ak.us/"
               "basis/commbr_info.asp?session=%s" % term)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'get_mbr_info')]"):
                if ("house=%s" % chamber_abbr) not in link.attrib['href']:
                    continue

                self.scrape_legislator(chamber, term, link.attrib['href'])

    def scrape_legislator(self, chamber, term, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            name = page.xpath('//h3')[1].text
            name = re.sub(r'\s+', ' ', name)
            name = name.replace('Senator', '').replace('Representative', '')
            name = name.strip()

            code = re.search(r'member=([A-Z]{3,3})&', url).group(1)

            district = page.xpath("//td[starts-with(text(), 'District:')]")
            district = district[0].text.replace("District:", "").strip()

            party = page.xpath("//td[starts-with(text(), 'Party:')]")
            party = party[0].text.replace("Party:", "").strip()

            leg = Legislator(term, chamber, district, name, party=party,
                             code=code)
            leg.add_source(url)

            self.save_legislator(leg)
