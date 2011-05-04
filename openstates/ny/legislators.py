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

                contact_link = link.xpath("../span[@class = 'contact']/a")[0]
                self.scrape_upper_contact_info(
                    legislator, contact_link.attrib['href'])

                self.save_legislator(legislator)

    def scrape_upper_contact_info(self, legislator, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            legislator.add_source(url)

            dist_str = page.xpath("string(//div[@class = 'district'])")
            match = re.match(r'\(([A-Za-z,\s]+)\)', dist_str)
            if match:
                party = match.group(1)
                party_map = {'D': 'Democratic', 'R': 'Republican',
                             'WF': 'Working Families',
                             'C': 'Conservative'}
                party = ', '.join(
                    [party_map.get(p.strip(), p.strip())
                     for p in party.split(',')])
                legislator['roles'][0]['party'] = party

            try:
                span = page.xpath("//span[. = 'Albany Office']/..")[0]
                cap_address = span.xpath("string(div[1])").strip()
                cap_address += "\nAlbany, NY 12247"
                legislator['capitol_address'] = cap_address

                phone = span.xpath("div[@class='tel']/span[@class='value']")[0]
                legislator['capitol_phone'] = phone.text.strip()
            except IndexError:
                # Sometimes contact pages are just plain broken
                pass

            try:
                span = page.xpath("//span[. = 'District Office']/..")[0]
                dist_address = span.xpath("string(div[1])").strip() + "\n"
                dist_address += span.xpath(
                    "string(span[@class='locality'])").strip() + ", "
                dist_address += span.xpath(
                    "string(span[@class='region'])").strip() + " "
                dist_address += span.xpath(
                    "string(span[@class='postal-code'])").strip()
                legislator['district_address'] = dist_address

                phone = span.xpath("div[@class='tel']/span[@class='value']")[0]
                legislator['district_phone'] = phone.text.strip()
            except IndexError:
                # No district office yet?
                pass

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
                district = district.rstrip('rthnds')

                legislator = Legislator(term, 'lower', district,
                                        name, party="Unknown")
                legislator.add_source(url)

                self.save_legislator(legislator)
