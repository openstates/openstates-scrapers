#!/usr/bin/env python
import re

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class NYLegislatorScraper(LegislatorScraper):
    state = 'ny'

    def scrape(self, chamber, term):
        if chamber == 'upper':
            self.scrape_upper(term)
        else:
            self.scrape_lower(term)

    def scrape_upper(self, term):
        url = "http://www.nysenate.gov/senators"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//span[@class='field-content']/a"):
                if not link.text:
                    continue
                name = link.text.strip()

                district = link.xpath("string(../../../div[3]/span[1])")
                district = re.match(r"District (\d+)", district).group(1)

                photo_link = link.xpath("../../../div[1]/span/a/img")[0]
                photo_url = photo_link.attrib['src']

                legislator = Legislator(term, 'upper', district,
                                        name, party="Unknown",
                                        photo_url=photo_url)
                legislator.add_source(url)

                self.save_legislator(legislator)

    def scrape_lower(self, term):
        url = "http://assembly.state.ny.us/mem/?sh=email"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for link in page.xpath("//a[contains(@href, '/mem/')]"):
                name = link.text.strip()
                if name == 'Assembly Members':
                    continue

                district = link.xpath("string(../following-sibling::"
                                      "div[@class = 'email2'][1])")
                district = district.rstrip('thnds')

                legislator = Legislator(term, 'lower', district,
                                        name, party="Unknown")
                legislator.add_source(url)

                self.save_legislator(legislator)
