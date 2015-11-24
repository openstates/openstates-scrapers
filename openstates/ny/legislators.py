import re
import itertools
import datetime
import lxml.html
import logging
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class NYLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ny'

    def _split_list_on_tag(self, elements, tag):
        data = []
        for element in elements:
            element_class = None

            try:
                element_class = element.attrib['class']
            except:
                pass
            
            if element_class == tag:
                yield data
                data = []
            else:
                data.append(element)

    def _identify_party(self):
        """
        Get the best available information on New York political party
        affiliations. Returns a dict mapping district to party for the
        New York State Assembly.

        The formatting of this page is pretty abysmal, so apologies
        about the dirtiness of this method.
        """
        # These may need to be changed, but should be mostly constant.
        NY_US_HOUSE_SEATS = 27
        NY_STATE_SENATE_SEATS = 63
        NY_STATE_ASSEMBLY_SEATS = 150
        SKIP_SEATS = NY_US_HOUSE_SEATS + NY_STATE_SENATE_SEATS

        # Download the page and ingest using lxml
        MEMBER_LIST_URL = 'http://www.elections.ny.gov:8080/reports/rwservlet'\
            '?cmdkey=nysboe_incumbnt'

        member_list_page = self.lxmlize(MEMBER_LIST_URL)

        # Map district to party affiliation
        congressional_affiliations = {}
        senate_affiliations = {}
        assembly_affiliations = {}
        district = None
        capture_district = False
        capture_party = False
        # Keeps track of place in incumbent listings.
        entry_counter = 0

        affiliation_text = self.get_nodes(
            member_list_page,
            '/html/body/table/tr/td/font[@color="#0000ff"]/b/text()')
        for affiliation in affiliation_text:
            if capture_district and capture_party:
                raise AssertionError('Assembly party parsing simultaneously'\
                    'looking for both district number and party name.')

            # Replace non-breaking spaces.
            affiliation = re.sub(r'\xa0', ' ', affiliation)

            # Ignore header text when parsing.
            try:
                datetime.datetime.strptime(affiliation, "%B %d, %Y")
                is_date = True
            except ValueError:
                is_date = False

            if is_date or affiliation == 'Elected Representatives for New York State by Office and District':
                continue
            # Otherwise, check to see if a District or Party is indicated.
            elif affiliation == u'District : ':
                capture_district = True
                continue 
            elif affiliation == u'Party : ':
                capture_party = True
                continue

            # If a search has been initiated for District or Party, then
            # capture them.
            if capture_district:
                district = affiliation
                assert district, 'No district found.'
                capture_district = False
            elif capture_party:
                # Skip capturing districts of members who are at-large, such as
                # governor.
                if not district:
                    capture_party = False
                    continue

                assert affiliation, 'No party is indicated for district {}'\
                    .format(district)

                # Districts listed in order: Congressional, State Senate,
                # then State Assembly.
                # If a repeat district is seen, assume it's from the
                # next body in that list.
                if (int(district) <= NY_US_HOUSE_SEATS and\
                    not congressional_affiliations.get(district)):
                    congressional_affiliations[district] = affiliation.title()
                elif (int(district) <= NY_STATE_SENATE_SEATS and\
                    not senate_affiliations.get(district)):
                    senate_affiliations[district] = affiliation.title()
                elif (int(district) <= NY_STATE_ASSEMBLY_SEATS and\
                    not assembly_affiliations.get(district)):
                    assembly_affiliations[district] = affiliation.title()
                else:
                    message = 'District {} appears too many times in party '\
                        'document.'
                    raise AssertionError(message.format(district))

                district = None
                capture_party = False
                entry_counter += 1                
            else:
                message = 'Assembly party parsing found bad text: "{}"'
                raise AssertionError(message.format(affiliation))

        return assembly_affiliations

    def _parse_office(self, office_node):
        """
        Gets the contact information from the provided office.
        """
        office_name_text = self.get_node(
            office_node,
            './/span[@itemprop="name"]/text()')

        if office_name_text is not None:
            office_name_text = office_name_text.strip()
        else:
            office_name_text = ()

        # Initializing default values for office attributes.
        office_name    = None
        office_type    = None
        street_address = None
        city           = None
        state          = None
        zip_code       = None
        address        = None
        phone          = None
        fax            = None

        # Determine office names/types consistent with Open States internal
        # format.
        if 'Albany Office' in office_name_text:
            office_name = 'Capitol Office'
            office_type = 'capitol'
        elif 'District Office' in office_name_text:
            office_name = 'District Office'
            office_type = 'district'
        else:
            # Terminate if not a capitol or district office.
            return None

        # Get office street address.
        street_address_text = self.get_node(
            office_node,
            './/div[@class="street-address"][1]/'
            'span[@itemprop="streetAddress"][1]/text()')

        if street_address_text is not None:
            street_address = street_address_text.strip()

        # Get office city.
        city_text = self.get_node(
            office_node,
            './/span[@class="locality"][1]/text()')

        if city_text is not None:
            city = city_text.strip()

        # Get office state.
        state_text = self.get_node(
            office_node,
            './/span[@class="region"][1]/text()')

        if state_text is not None:
            state = state_text.strip()

        # Get office postal code.
        zip_code_text = self.get_node(
            office_node,
            './/span[@class="postal-code"][1]/text()')

        if zip_code_text is not None:
            zip_code = zip_code_text.strip()

        # Build office physical address.
        if (street_address is not None and
            city is not None and
            state is not None and
            zip_code is not None):
            address = "{}\n{}, {} {}".format(
                street_address, city, state, zip_code)
        else:
            address = None

        # Get office phone number.
        phone_node = self.get_node(
            office_node,
            './/div[@class="tel"]/span[@itemprop="telephone"]')

        if phone_node is not None:
            phone = phone_node.text.strip()

        # Get office fax number.
        fax_node = self.get_node(
            office_node,
            './/div[@class="tel"]/span[@itemprop="faxNumber"]')

        if fax_node is not None:
            fax = fax_node.text.strip()

        office = dict(
            name=office_name,
            type=office_type,
            phone=phone,
            fax=fax,
            address=address)

        return office

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber + '_chamber')(term)

    def scrape_upper_chamber(self, term):
        url = 'http://www.nysenate.gov/senators-committees'

        page = self.lxmlize(url)

        legislator_nodes = page.xpath(
            '//div[contains(@class, "u-even") or contains(@class, "u-odd")]/a')

        for legislator_node in legislator_nodes:
            legislator_url = legislator_node.attrib['href']

            # Find element containing senator data.
            info_node = self.get_node(
                legislator_node,
                './/div[@class="nys-senator--info"]')

            # Skip legislator if information is missing entirely.
            if info_node is None:
                warning = 'No information found for legislator at {}.'
                self.logger.warning(warning.format(legislator_url))
                continue

            # Initialize default values for legislator attributes.
            name      = None
            district  = None
            party     = None
            photo_url = None

            # Find legislator's name.
            name_node = self.get_node(
                info_node,
                'h4[@class="nys-senator--name"]')

            if name_node is not None:
                name = name_node.text.strip()
            else:
                # Skip the legislator if a name cannot be found.
                continue

            # Find legislator's district number.
            district_node = self.get_node(
                info_node,
                './/span[@class="nys-senator--district"]')

            if district_node is not None:
                district_text = district_node.xpath('.//text()')[2]
                district = re.sub(r'\D', '', district_text)

            # Find legislator's party affiliation.
            party_node = self.get_node(
                district_node,
                './/span[@class="nys-senator--party"]')

            if party_node is not None:
                party_text = party_node.text.strip()

                if party_text.startswith('(D'):
                    party = 'Democratic'
                elif party_text.startswith('(R'):
                    party = 'Republican'
                else:
                    raise ValueError('Unexpected party affiliation: {}'
                        .format(party_text))

            # Find legislator's profile photograph.
            photo_node = self.get_node(
                legislator_node,
                './/div[@class="nys-senator--thumb"]/img')

            if photo_node is not None:
                photo_url = photo_node.attrib['src']

            legislator = Legislator(
                full_name=name,
                term=term,
                chamber='upper',
                district=district,
                party=party,
                photo_url=photo_url
            )

            legislator.add_source(url)
            legislator['url'] = legislator_url

            # Find legislator's offices.
            contact_url = legislator_url + '/contact'
            self.scrape_upper_offices(legislator, contact_url)

            self.save_legislator(legislator)

    def scrape_upper_offices(self, legislator, url):
        legislator_page = self.lxmlize(url)

        legislator.add_source(url)

        # Find legislator e-mail address.
        email_node = self.get_node(
            legislator_page,
            '//div[contains(concat(" ", normalize-space(@class), " "), '
            '" c-block--senator-email ")]/div/a[contains(@href, "mailto:")]')

        if email_node is not None:
            email_text = email_node.attrib['href']
            email = re.sub(r'^mailto:', '', email_text)
            legislator['email'] = email
        else:
            email = None

        # Parse all offices.
        office_nodes = self.get_nodes(
            legislator_page,
            '//div[@class="adr"]')

        for office_node in office_nodes:
            office = self._parse_office(office_node)

            if office is not None:
                legislator.add_office(**office)

    def scrape_lower_chamber(self, term):
        url = 'http://assembly.state.ny.us/mem/?sh=email'

        page = self.lxmlize(url)

        district_affiliations = self._identify_party()

        assembly_member_nodes = self.get_nodes(
            page,
            '//div[@id="maincontainer"]/div[contains(@class, "email")]')

        for assembly_member_node in self._split_list_on_tag(
            assembly_member_nodes, 'emailclear'):
            try:
                name_node, district_node, email_node = assembly_member_node
            except ValueError:
                name_node, district_node = assembly_member_node
                email_node = None

            name_anchor = self.get_node(
                name_node,
                './/a[contains(@href, "/mem/")]')
            name = name_anchor.text.strip()
            # Skip non-seats.
            if name == 'Assembly Members':
                continue
            if 'Assembly District' in name:
                continue

            if email_node is not None:
                email_anchor = self.get_node(
                    email_node,
                    './/a[contains(@href, "mailto")]')
                if email_anchor is not None:
                    email = email_anchor.text.strip()

            if district_node is not None:
                district = district_node.text.rstrip('rthnds')

            party = district_affiliations[district].strip()
            if not party or party is None:
                self.logger.warn('Vacant seat in District {}.'.format(district))
                continue

            photo_url = 'http://assembly.state.ny.us/mem/pic/{0:03d}.jpg'\
                .format(int(district))

            legislator_url = name_anchor.get('href')

            legislator = Legislator(
                term,
                'lower',
                district,
                name,
                party=party,
                url=legislator_url,
                photo_url=photo_url)
            legislator.add_source(url)

            self.scrape_lower_offices(legislator_url, legislator, email)

            self.save_legislator(legislator)

    def scrape_lower_offices(self, url, legislator, email=None):
        legislator.add_source(url)

        page = self.lxmlize(url)

        offices = False

        for data in page.xpath('//div[@class="officehdg"]'):
            data = (data.xpath('text()'),
                    data.xpath('following-sibling::div[1]/text()'))
            ((office_name,), address) = data

            if 'district' in office_name.lower():
                office_type = 'district'
            else:
                office_type = 'capitol'

            address = [x.strip() for x in address if x.strip()]

            fax = None
            if address[-1].startswith("Fax: "):
                fax = address.pop().replace("Fax: ", "")

            phone = None
            if re.search(r'\d{3}[-\s]?\d{3}[-\s]?\d{4}', address[-1]):
                phone = address.pop()

            address = '\n'.join(address)

            legislator.add_office(
                    name=office_name,
                    type=office_type,
                    phone=phone,
                    fax=fax,
                    address=address,
                    email=email
                    )

            offices = True

        if not offices and email:
            legislator.add_office(
                type="capitol",
                name="Capitol Office",
                email=email)
