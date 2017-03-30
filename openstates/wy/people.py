import re

import lxml.html
from pupa.scrape import Scraper, Person


class WYPersonScraper(Scraper):
    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        chamber_abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

        url = ("http://legisweb.state.wy.us/LegislatorSummary/LegislatorList"
               ".aspx?strHouse=%s&strStatus=N" % chamber_abbrev)
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'LegDetail')]"):
            name = link.text.strip()
            # Remove district number from member names
            name = re.sub(r'\s\([HS]D\d{2}\)$', "", name)
            leg_url = link.get('href')

            email_address = link.xpath("../../../td[1]//a")[0].attrib['href']
            email_address = link.xpath("../../../td[2]//a")[0].attrib['href']
            email_address = email_address.split('Mailto:')[1]

            party = link.xpath("string(../../../td[3])").strip()
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'

            district = link.xpath(
                "string(../../../td[4])").strip().lstrip('HS0')

            leg_page = lxml.html.fromstring(self.get(leg_url).text)
            leg_page.make_links_absolute(leg_url)
            img = leg_page.xpath(
                "//img[contains(@src, 'LegislatorSummary/photos')]")[0]
            photo_url = img.attrib['src']

            office_tds = leg_page.xpath('//table[@id="ctl00_cphContent_tblContact"]/tr/td/text()')
            address = []
            phone = None
            fax = None

            for td in office_tds:
                if td.startswith('Home - '):
                    phone = td.strip('Home - ')
                elif td.startswith('Cell -'):
                    phone = td.strip('Cell - ')
                elif td.startswith('Work -'):
                    phone = td.strip('Work - ')

                if td.startswith('Fax -'):
                    fax = td.strip('Fax - ')

                elif ' - ' not in td:
                    address.append(td)

            person = Person(
                name=name,
                district=district,
                party=party,
                primary_org=chamber,
                image=photo_url,
            )

            adr = " ".join([part.strip() for part in address]) or None

            person.add_contact_detail(type='address', value=adr, note='District Office')
            if phone:
                person.add_contact_detail(type='voice', value=phone, note='District Office')
            if fax:
                person.add_contact_detail(type='fax', value=fax, note='District Office')

            person.add_source(url)
            person.add_source(leg_url)
            person.add_link(leg_url)

            yield person
