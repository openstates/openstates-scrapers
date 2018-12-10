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
    'C': 'Independent',
    # Chapman (unenrolled)
    'G': 'Independent',
}


def clean_phone(phone):
    if phone:
        if sum(c.isdigit() for c in phone) == 7:
            phone = '(207) ' + phone
    return phone


class MEPersonScraper(Scraper):
    def scrape(self, chamber=None):
        # if chamber in ['upper', None]:
        #     yield from self.scrape_senators()
        if chamber in ['lower', None]:
            yield from self.scrape_reps()

    def scrape_rep(self, url):

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        name = page.xpath('//div[@class="member-name"]/text()')[0].strip()
        district_number = page.xpath('//span[contains(text(), "House District:")]/following-sibling::span/text()')[0].strip()
        email = page.xpath('//a[./i[contains(@class,"fa-envelope")]]/text()')[0].strip()

        photo_url = page.xpath('//header[@id="home"]/img/@src')[0]

        party = self.get_rep_table_by_header(page, 'Party Affiliation')
        address = self.get_rep_table_by_header(page, 'Office Address')

        person = Person(
            name=name,
            district=district_number,
            primary_org='lower',
            party=party,
            image=photo_url,
        )

        person.add_source(url)

        yield person

    def get_rep_table_by_header(self, page, header):
        if page.xpath('//td[contains(text(), "{}")]/following-sibling::td'.format(header)):
            return page.xpath('//td[contains(text(), "{}")]/following-sibling::td/text()'.format(header))[0].strip()
        return None

    def scrape_reps(self):
        url = 'https://legislature.maine.gov/house/house/MemberProfiles/ListAlpha'
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        # These do not include the non-voting tribal representatives
        # They do not have numbered districts, and lack a good deal of
        # the standard profile information about representatives
        for link in page.xpath('//a[contains(@href, "house/MemberProfiles/Details")]/@href'):
            print(link)
            yield from self.scrape_rep(link)
            continue

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
                    (?P<party>[DRCUIG])
                    -
                    (?P<district_name>.+?)
                    \)
                    '''
            info_search = re.search(INFO_RE, leg_info, re.VERBOSE)

            if not info_search:
                leg_url = district.xpath('a[3]/@href')[0]
                leg_info_second_active = district.xpath('a[3]/text()')[0]

                member_name = leg_info_second_active
                mem_info = district.xpath('a[3]/following-sibling::text()')
                party = _party_map[mem_info[0][2]]
                district = mem_info[0].split('-')[1][:-1]
            else:
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

            person = Person(
                name=member_name,
                district=district_number,
                primary_org='lower',
                party=party,
                image=photo_url,
            )
            person.extras['district_name'] = district_name

            person.add_link(leg_url)
            person.add_source(leg_url)

            if office_address:
                leg_address = office_address
                person.add_contact_detail(
                    type='address', value=leg_address, note='District Office')
            else:
                # If no address for legislator
                if party == 'Democratic':
                    leg_address = (
                        'House Democratic Office, Room 333 State House, 2 State House Station, '
                        'Augusta, Maine 04333-0002'
                    )

                    person.add_contact_detail(
                        type='address', value=leg_address, note='Party Office')

                elif party == 'Republican':
                    leg_address = (
                        'House GOP Office, Room 332 State House, 2 State House Station, '
                        'Augusta, Maine 04333-0002'
                    )

                    person.add_contact_detail(
                        type='address', value=leg_address, note='Party Office')

            if office_email:
                office_email = office_email[0]
                person.add_contact_detail(type='email', value=office_email, note='District Office')
            if business_phone:
                person.add_contact_detail(
                    type='voice', value=clean_phone(business_phone.group(1)),
                    note='Business Phone')
            if home_phone:
                person.add_contact_detail(
                    type='voice', value=clean_phone(home_phone.group(1)),
                    note='Home Phone')
            if cell_phone:
                person.add_contact_detail(
                    type='voice', value=clean_phone(cell_phone.group(1)),
                    note='Cell Phone')

            yield person

    def scrape_senators(self):
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

        url = (
            'https://mainelegislature.org/uploads/visual_edit/'
            '128th-senate-members-for-distribution-1.xlsx'
        )
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
                continue  # Seat is vacant

            html = self.get(leg_url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(leg_url)
            xpath = '//img[contains(@src, ".png")]/@src'
            photo_url = doc.xpath(xpath)
            if photo_url:
                photo_url = photo_url.pop()
            else:
                photo_url = None

            person = Person(
                name=full_name,
                district=district,
                image=photo_url,
                primary_org='upper',
                party=party,
            )

            person.add_link(leg_url)
            person.add_source(leg_url)
            person.extras['first_name'] = first_name
            person.extras['middle_name'] = middle_name
            person.extras['last_name'] = last_name

            person.add_contact_detail(type='address', value=address, note='District Office')
            if phone:
                person.add_contact_detail(
                    type='voice', value=clean_phone(phone), note='District Phone')
            person.add_contact_detail(type='email', value=d['email'], note='District Email')

            yield person
