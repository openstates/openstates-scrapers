from pupa.scrape import Scraper
from pupa.scrape import Person
import lxml.html

CHAMBER_URLS = {
    'upper': 'http://ilga.gov/senate/default.asp?GA={term}',
    'lower': 'http://ilga.gov/house/default.asp?GA={term}',
}

CHAMBER_ROLES = {'upper' : 'Senator',
                 'lower' : 'Representative'}

BIRTH_DATES = {'Daniel Biss' : '1977-08-27'}

class IlPersonScraper(Scraper):
    def scrape(self):
        for member, chamber, term, url in self._memberships():
            name, _, _, district, party = member.xpath('td')
            district = district.text
            detail_url = name.xpath('a/@href')[0]
            
            if party.text_content().strip() == "":
                self.warning("Garbage party: Skipping!")
                continue
            
            party = {'D':'Democratic', 'R': 'Republican',
                     'I': 'Independent'}[party.text]
            name = name.text_content().strip()
            
            # inactive legislator, skip them for now
            if name.endswith('*'):
                name = name.strip('*')
                continue
            
            p = Person(name,
                       district=district,
                       primary_org=chamber, 
                       role=CHAMBER_ROLES[chamber],
                       party=party)

            p.add_source(url)

            birth_date = BIRTH_DATES.get(name, None)
            if birth_date:
                p.birth_date = birth_date
            
            leg_html = self.get(detail_url).text
            leg_doc = lxml.html.fromstring(leg_html)
            leg_doc.make_links_absolute(detail_url)

            hotgarbage = (
                'Senate Biography Information for the 98th General '
                'Assembly is not currently available.')

            if hotgarbage in leg_html:
                # The legislator's bio isn't available yet.
                self.logger.warning('No legislator bio available for ' + name)
                yield p
                continue


            photo_url = leg_doc.xpath('//img[contains(@src, "/members/")]/@src')[0]
            p.image = photo_url

            # email
            email = leg_doc.xpath('//b[text()="Email: "]')
            if email:
                p.add_contact_detail(type='email', value=email[0].tail.strip())

            offices = {'capitol' : '//table[contains(string(), "Springfield Office")]',
                       'district' : '//table[contains(string(), "District Office")]'}

            for location, xpath in offices.items():
                table = leg_doc.xpath(xpath)
                if table:
                    addr, phone, fax = self._table_to_office(table[3])
                    if addr:
                        p.add_contact_detail(type='address', value=addr, note=location)
                    if phone:
                        p.add_contact_detail(type='voice', value=phone, note=location)
                    if fax:
                        p.add_contact_detail(type='fax', value=fax, note=location)


            yield p

    # function for turning an IL contact info table to office details
    def _table_to_office(self, table):
        addr = ''
        phone = None
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

        return addr, phone, fax
            
        

    def _memberships(self):
        for term in range(99, 100):
            for chamber, base_url in CHAMBER_URLS.items():
                url = base_url.format(term=term)
                
                html = self.get(url).text
                page = lxml.html.fromstring(html)
                page.make_links_absolute(url)

                for row in page.xpath('//table')[4].xpath('tr')[2:]:
                    yield row, chamber, term, url
