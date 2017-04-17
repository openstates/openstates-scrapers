import re
from pupa.scrape import Person, Scraper

import lxml.html
import xlrd

_party_map = {
    'D': 'Democratic',
    'R': 'Republican',
    'U': 'Independent',
    'I': 'Independent',
    # Common Sense Independent Party
    'C': 'Independent'
}

class MEPersonScraper(Scraper):
    jurisdiction = 'me'

    def scrape(self, chamber=None):

        if chamber == None:
            chamber = ['upper', 'lower']
        if 'upper' in chamber:
            yield from self.scrape_senators(chamber)
        if 'lower' in chamber:
            yield from self.scrape_reps(chamber)

    def scrape_reps(self, chamber):
        url = 'http://www.maine.gov/legis/house/dist_mem.htm'
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        # These do not include the non-voting tribal representatives
        # They do not have numbered districts, and lack a good deal of
        # the standard profile information about representatives
        for district in page.xpath('//a[contains(@href, "dist_twn")]/..'):
            if "- Vacant" in district.text_content():
                self.warning("District is vacant: '{}'".
                             format(district.text_content()))
                continue

            _, district_number = district.xpath('a[1]/@href')[0].split('#')

            leg_url = district.xpath('a[2]/@href')[0]
            leg_info = district.xpath('a[2]/text()')[0]

            INFO_RE = r'''
                    Representative\s
                    (?P<member_name>.+?)
                    \s\(
                    (?P<party>[DRCUI])
                    -
                    (?P<district_name>.+?)
                    \)
                    '''
            info_search = re.search(INFO_RE, leg_info, re.VERBOSE)

            member_name = info_search.group('member_name')
            party = _party_map[info_search.group('party')]
            district_name = info_search.group('district_name')

            # Get the photo url.
            html = self.get(leg_url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(leg_url)
            (photo_url,) = doc.xpath('//img[contains(@src, ".jpg")]/@src')

            # Add contact information from personal page
            office_address = re.search(
                    r'<B>Address:  </B>(.+?)\n?</?P>', html, re.IGNORECASE).group(1)

            office_email = doc.xpath(
                    '//a[starts-with(@href, "mailto:")]/text()')
            business_phone = re.search(
                    r'<B>Business Telephone:  </B>(.+?)</?P>', html, re.IGNORECASE)
            home_phone = re.search(
                    r'<B>Home Telephone:  </B>(.+?)</?P>', html, re.IGNORECASE)
            cell_phone = re.search(
                    r'<B>Cell Telephone:  </B>(.+?)</?P>', html, re.IGNORECASE)

            person = Person(name=member_name, district=district_name, party=party, image=photo_url)

            person.add_link(leg_url)
            person.add_source(leg_url)

            if office_address:
                leg_address = office_address
                person.add_contact_detail(type='address', value=leg_address, note='District Office')
            else:
                # If no address for legislator
                if party == 'Democratic':
                    leg_address = 'House Democratic Office, Room 333 State House, 2 State House Station, Augusta, Main 04333-0002'

                    person.add_contact_detail(type='address', value=leg_address, note='Party Office')

                elif party == 'Republican':
                    leg_address = 'House GOP Office, Room 332 State House, 2 State House Station, Augusta, Main 04333-0002'

                    person.add_contact_detail(type='address', value=leg_address, note='Party Office')

            if office_email:
                office_email = office_email[0]
                person.add_contact_detail(type='email', value=office_email, note='District Office')
            if business_phone:
                person.add_contact_detail(type='voice', value=business_phone.group(1), note='Business Phone')
            if home_phone:
                person.add_contact_detail(type='voice', value=home_phone.group(1), note='Home Phone')
            if cell_phone:
                person.add_contact_detail(type='voice', value=cell_phone.group(1), note='Cell Phone')

            yield person

    def scrape_senators(self, chamber):
        mapping = {
                'district': 0,
                'first_name': 2,
                'middle_name': 3,
                'last_name': 4,
                'suffixes': 5,
                'party': 1,
                'street_addr': 6,
                'city': 7,
                'state': 8,
                'zip_code': 9,
                'phone1': 10,
                'phone2': 11,
                'email': 12
        }

        url = 'https://mainelegislature.org/uploads/visual_edit/128th-senate-members-for-distribution-1.xlsx'
        fn, result = self.urlretrieve(url)

        wb = xlrd.open_workbook(fn)
        sh = wb.sheet_by_index(0)

        LEGISLATOR_ROSTER_URL = \
            'https://mainelegislature.org/senate/128th-senators/9332'
        roster_doc = lxml.html.fromstring(self.get(LEGISLATOR_ROSTER_URL).text)
        roster_doc.make_links_absolute(LEGISLATOR_ROSTER_URL)

        for rownum in range(1, sh.nrows):
            # get fields out of mapping
            d = {}
            for field, col_num in mapping.items():
                try:
                    d[field] = str(sh.cell(rownum, col_num).value).strip()
                except IndexError:
                    # This col_num doesn't exist in the sheet.
                    pass
            first_name = d['first_name']
            middle_name = d['middle_name']
            last_name = d['last_name']

            full_name = " ".join((first_name, middle_name,
                                  last_name))
            full_name = re.sub(r'\s+', ' ', full_name).strip()

            address = "{street_addr}\n{city}, ME {zip_code}".format(**d)

            # For matching up legs with votes
            district_name = d['city']

            phone = d['phone1']
            if not phone:
                phone = d['phone2']
            if not phone:
                phone = None

            district = d['district'].split('.')[0]
            party = d['party'].split('.')[0]

            # Determine legislator's URL to get their photo
            URL_XPATH = '//li/a[contains(text(), "District {:02d}")]/@href'.format(int(district))

            try:
                (leg_url, ) = roster_doc.xpath(URL_XPATH)
            except ValueError:
                self.warning('vacant seat %s', district)
                continue # Seat is vacant

            html = self.get(leg_url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(leg_url)
            xpath = '//img[contains(@src, ".png")]/@src'
            photo_url = doc.xpath(xpath)
            if photo_url:
                photo_url = photo_url.pop()
            else:
                photo_url = None

            person = Person(name=full_name, district=district,  image=photo_url, primary_org=chamber, party=party)

            person.add_link(leg_url)
            person.add_source(leg_url)
            person.extras['first_name'] = first_name
            person.extras['middle_name'] = middle_name
            person.extras['last_name'] = last_name

            person.add_contact_detail(type='address', value=address, note='District Office')
            person.add_contact_detail(type='voice', value=phone, note='District Phone')
            person.add_contact_detail(type='email', value=d['email'], note='District Email')

            yield person
