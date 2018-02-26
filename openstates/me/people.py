import re
from pupa.scrape import Person, Scraper

import lxml.html
import xlrd
import scrapelib

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
        if chamber in ['upper', None]:
            yield from self.scrape_senators()
        if chamber in ['lower', None]:
            yield from self.scrape_reps()

    def scrape_reps(self):
        mapping = {
            'district': 0,
            'last_name': 1,
            'first_name': 2,
            'mid_name': 3,
            'jr_sr': 4,
            'party': 5,
            'legal_res': 6,
            'address1': 7,
            'address2': 8,
            'town': 9,
            'state': 10,
            'zip_code': 11,
            'zip_plus4': 12,
            'home_phone': 13,
            'cell_phone': 14,
            'business_phone': 15,
            'other_phone': 16,
            'fax': 17,
            'email': 18,
            'seat_no': 19,
            'house_leadership': 20,
            'committees': 21
        }

        url = 'http://legislature.maine.gov/house/' + str(self.latest_session()) + 'house.xlsx'
        fn, result = self.urlretrieve(url)

        wb = xlrd.open_workbook(fn)
        sh = wb.sheet_by_index(0)

        LEGISLATOR_ROSTER_URL = \
            'http://legislature.maine.gov/house/dist_mem.htm'
        roster_doc = lxml.html.fromstring(self.get(LEGISLATOR_ROSTER_URL).text)
        roster_doc.make_links_absolute(LEGISLATOR_ROSTER_URL)

        for rownum in range(1, sh.nrows):
            # get fields out of mapping
            d = {}
            for field, col_num in mapping.items():
                try:
                    d[field] = str(sh.cell(rownum, col_num).value).strip()
                except UnicodeEncodeError:
                    # str typecasting will raise error for non-ascii characters.
                    d[field] = sh.cell(rownum, col_num).value.encode('utf-8').strip()

            try:
                # xlrd reads this value as a float. However we save it as a string.
                district_number = str(int(float(d['district'])))
            except ValueError:
                # Will reach here in case district number is blank. We will skip this row.
                continue

            district_name = d['legal_res']

            first_name = d['first_name']
            middle_name = d['mid_name']
            last_name = d['last_name']
            jr_sr = d['jr_sr']

            # Little tricky. Column header says jr_sr, but this can be any suffix.
            # If comma incorrectly placed, string matching for extracting URL from roster breaks.
            if jr_sr in ['Jr.', 'Sr.']:
                last_name += ', ' + jr_sr
            elif jr_sr:
                last_name += ' ' + jr_sr

            member_name = " ".join((first_name, middle_name, last_name))
            member_name = re.sub(r'\s+', ' ', member_name).strip()

            party = d['party']
            party = _party_map[party]

            # Determine legislator's URL to get their photo.
            # Roster URL list does not include nicknames, have to be removed before we search.
            if '"' in middle_name:
                # Name contains nickname
                roster_name = " ".join((first_name, ''.join(middle_name.split('"')[2:]),
                                        last_name))
                roster_name = re.sub(r'\s+', ' ', roster_name).strip()
            else:
                roster_name = member_name

            URL_XPATH = '//a[contains(text(), "{}")]/@href'.format(roster_name)
            try:
                (leg_url, ) = roster_doc.xpath(URL_XPATH)
            except ValueError:
                self.warning("Could not find legislator URL for {}".format(member_name))

            # Determine legislator's URL to get their photo
            photo_url = leg_url[:-4] + '.jpg'
            photo_url = photo_url.split('/')
            photo_url[4] = 'photo' + str(self.latest_session())
            photo_url = '/'.join(photo_url)

            try:
                self.head(leg_url)
            except scrapelib.HTTPError:
                self.warning("Could not correctly guess photo URL for {}".format(member_name))

            # Contact Information
            office_address = "{address2}\n{town}, ME {zip_code}".format(**d)
            office_email = d['email']
            business_phone = d['business_phone']
            home_phone = d['home_phone']
            cell_phone = d['cell_phone']

            person = Person(
                name=member_name,
                district=district_number,
                primary_org='lower',
                party=party,
                image=photo_url,
            )

            person.extras['district_name'] = district_name

            person.add_link(leg_url)
            person.add_source(url)

            if office_address:
                leg_address = office_address
                person.add_contact_detail(
                    type='address', value=leg_address, note='District Office')

            if office_email:
                person.add_contact_detail(type='email', value=office_email, note='Capitol Office')

            if business_phone:
                person.add_contact_detail(
                    type='voice', value=clean_phone(business_phone),
                    note='Business Phone')

            if home_phone:
                person.add_contact_detail(
                    type='voice', value=clean_phone(home_phone),
                    note='Home Phone')

            if cell_phone:
                person.add_contact_detail(
                    type='voice', value=clean_phone(cell_phone),
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
            'https://mainelegislature.org/uploads/visual_edit/' +
            str(self.latest_session()) +
            'th-senate-members-for-distribution-1.xlsx'
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
