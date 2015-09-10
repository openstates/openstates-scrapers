# -*- coding: utf-8 -*-
from urlparse import urlparse
from urllib import quote

import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator

MEMBER_LIST_URL = {
    'upper': 'http://ilga.gov/senate/default.asp?GA=%s',
    'lower': 'http://ilga.gov/house/default.asp?GA=%s',
}


class ILLegislatorScraper(LegislatorScraper):
    jurisdiction = 'il'

    def scrape(self, chamber, term):
        term_slug = term[:-2]
        url = MEMBER_LIST_URL[chamber] % term_slug

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for row in doc.xpath('//table')[4].xpath('tr')[2:]:
            name, _, _, district, party = row.xpath('td')
            district = district.text

            if party.text_content().strip() == "":
                self.warning("Garbage party: Skipping!")
                continue

            party = {'D':'Democratic', 'R': 'Republican',
                     'I': 'Independent'}[party.text]
            leg_url = name.xpath('a/@href')[0]
            name = name.text_content().strip()

            # inactive legislator, skip them for now
            if name.endswith('*'):
                name = name.strip('*')
                continue

            leg_html = self.get(leg_url).text
            leg_doc = lxml.html.fromstring(leg_html)
            leg_doc.make_links_absolute(leg_url)

            leg = Legislator(term, chamber, district, name, party=party,
                             url=leg_url)
            leg.add_source(url)

            hotgarbage = (
                'Senate Biography Information for the 98th General '
                'Assembly is not currently available.')
            if hotgarbage in leg_html:
                # The legislator's bio isn't available yet.
                self.logger.warning('No legislator bio available for ' + name)
                self.save_legislator(leg)
                continue

            photo_url = leg_doc.xpath('//img[contains(@src, "/members/")]/@src')[0]
            photo_url_parsed = urlparse(photo_url)
            encoded_path = quote(photo_url_parsed.path)
            photo_url = photo_url_parsed._replace(path=encoded_path).geturl()
            leg.update(photo_url=photo_url)
            leg.add_source(leg_url)

            # email
            email = leg_doc.xpath('//b[text()="Email: "]')
            if email:
                email = email[0].tail.strip()
            else:
                email = None

            # function for turning an IL contact info table to office details
            def _table_to_office(table, office_type, office_name, email=None):
                addr = ''
                phone = ''
                fax = None
                for row in table.xpath('tr'):
                    row = row.text_content().strip()
                    # skip rows that aren't part of address
                    if 'Office:' in row or row == 'Cook County':
                        continue
                    # fax number row ends with FAX
                    elif 'FAX' in row:
                        fax = row.replace(' FAX', '')
                    # phone number starts with ( [make it more specific?]
                    elif row.startswith('('):
                        phone = row
                    # everything else is an address
                    else:
                        addr += (row + '\n')
                if addr.strip() != ',':
                    leg.add_office(office_type, office_name,
                                   address=addr.strip(), phone=phone, fax=fax, email=email)

            # extract both offices from tables
            table = leg_doc.xpath('//table[contains(string(), "Springfield Office")]')
            if table:
                _table_to_office(table[3], 'capitol', 'Springfield Office', email)
            table = leg_doc.xpath('//table[contains(string(), "District Office")]')
            if table:
                _table_to_office(table[3], 'district', 'District Office')

            self.save_legislator(leg)
