import re
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import xlrd

_party_map = {'D': 'Democratic', 'R': 'Republican', 'U': 'Independent',
              'I': 'Independent'}


class MELegislatorScraper(LegislatorScraper):
    jurisdiction = 'me'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            self.scrape_senators(chamber, term)
        elif chamber == 'lower':
            self.scrape_reps(chamber, term)

    def scrape_reps(self, chamber, term_name):
        url = 'http://www.maine.gov/legis/house/dist_mem.htm'
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        # These do not include the non-voting tribal representatives
        # They do not have numbered districts, and lack a good deal of
        # the standard profile information about representatives
        districts = [x for x in page.xpath('/html/body/p') if
                len(x.xpath('a')) == 3]
        for district in districts:
            if "- Vacant" in district.text_content():
                self.warning("District is vacant: '{}'".
                             format(district.text_content()))
                continue

            district_number = district.xpath('a[1]/@name')[0]

            leg_url = district.xpath('a[3]/@href')[0]
            leg_info = district.xpath('a[3]/text()')[0]

            INFO_RE = r'''
                    Representative\s
                    (?P<member_name>.+?)
                    \s\(
                    (?P<party>[DRUI])
                    -
                    (?P<district_name>.+?)
                    \)
                    '''
            info_search = re.search(INFO_RE, leg_info, re.VERBOSE)

            member_name = info_search.group('member_name')
            party = _party_map[info_search.group('party')]
            district_name = info_search.group('district_name')

            leg = Legislator(term_name, chamber, str(district_number),
                             member_name, party=party, url=leg_url,
                             district_name=district_name)
            leg.add_source(url)
            leg.add_source(leg_url)

            # Get the photo url.
            html = self.get(leg_url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(leg_url)
            (photo_url, ) = doc.xpath('//img[contains(@src, ".jpg")]/@src')
            leg['photo_url'] = photo_url

            # Add contact information from personal page
            office_address = re.search(
                    r'<B>Address:  </B>(.+?)<P>', html, re.IGNORECASE).group(1)

            office_email = doc.xpath(
                    '//a[starts-with(@href, "mailto:")]/text()')
            if office_email:
                office_email = office_email[0]
            else:
                office_email = None
            
            business_phone = re.search(
                    r'<B>Business Telephone:  </B>(.+?)<P>', html, re.IGNORECASE)
            home_phone = re.search(
                    r'<B>Home Telephone:  </B>(.+?)<P>', html, re.IGNORECASE)
            cell_phone = re.search(
                    r'<B>Cell Telephone:  </B>(.+?)<P>', html, re.IGNORECASE)

            if business_phone:
                office_phone = business_phone.group(1)
            elif home_phone:
                office_phone = home_phone.group(1)
            elif cell_phone:
                office_phone = cell_phone.group(1)
            else:
                office_phone = None

            district_office = {
                    'name': "District Office",
                    'type': "district",
                    'address': office_address,
                    'fax': None,
                    'email': office_email,
                    'phone': office_phone
            }
            leg.add_office(**district_office)

            # Add state party office to member's addresses
            if party == "Democratic":
                DEM_PARTY_OFFICE = dict(
                        name='House Democratic Office',
                        type='capitol',
                        address='\n'.join(
                                ['Room 333, State House',
                                '2 State House Station',
                                'Augusta, Maine 04333-0002']),
                        fax=None,
                        email=None,
                        phone='(207) 287-1430')
                leg.add_office(**DEM_PARTY_OFFICE)
            elif party == "Republican":
                REP_PARTY_OFFICE = dict(
                        name='House GOP Office',
                        type='capitol',
                        address='\n'.join(
                                ['Room 332, State House',
                                '2 State House Station',
                                'Augusta, Maine 04333-0002']),
                        fax=None,
                        email=None,
                        phone='(207) 287-1440')
                leg.add_office(**REP_PARTY_OFFICE)

            # Save legislator
            self.save_legislator(leg)

    def scrape_senators(self, chamber, term):
        session = ((int(term[0:4]) - 2009) / 2) + 124

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

        list_location = '2014/12/127th-Senate-Members2'
        url = ('http://legisweb1.mainelegislature.org/wp/senate/'
                'wp-content/uploads/sites/2/{}.xlsx'.format(list_location))
        fn, result = self.urlretrieve(url)

        wb = xlrd.open_workbook(fn)
        sh = wb.sheet_by_index(0)

        LEGISLATOR_ROSTER_URL = \
            'http://legisweb1.mainelegislature.org/wp/senate/senators/'
        roster_doc = lxml.html.fromstring(self.get(LEGISLATOR_ROSTER_URL).text)
        roster_doc.make_links_absolute(LEGISLATOR_ROSTER_URL)

        for rownum in xrange(1, sh.nrows):
            # get fields out of mapping
            d = {}
            for field, col_num in mapping.iteritems():
                try:
                    d[field] = str(sh.cell(rownum, col_num).value).strip()
                except IndexError:
                    # This col_num doesn't exist in the sheet.
                    pass

            full_name = " ".join((d['first_name'], d['middle_name'],
                                  d['last_name']))
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

            # Determine legislator's URL to get their photo

            URL_XPATH = '//address[contains(text(), "(District {})")]/a/@href'. \
                    format(district)

            try:
                (leg_url, ) = roster_doc.xpath(URL_XPATH)
            except ValueError:
                continue # Seat is vacant

            leg = Legislator(term, chamber, district, full_name,
                             first_name=d['first_name'],
                             middle_name=d['middle_name'],
                             last_name=d['last_name'],
                             party=d['party'],
                             suffixes=d['suffixes'],
                             district_name=district_name,
                             url=leg_url)
            leg.add_source(url)
            leg.add_source(leg_url)

            html = self.get(leg_url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(leg_url)
            xpath = '//img[contains(@src, ".png")]/@src'
            photo_url = doc.xpath(xpath)
            if photo_url:
                photo_url = photo_url.pop()
                leg['photo_url'] = photo_url
            else:
                photo_url = None

            office = dict(
                name='District Office',
                type='district',
                phone=phone,
                fax=None,
                email=d['email'],
                address=address
                )

            leg.add_office(**office)
            self.save_legislator(leg)
