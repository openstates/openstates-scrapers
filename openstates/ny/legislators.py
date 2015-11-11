import re
import itertools
import datetime
import lxml.html
import logging
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class NYLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ny'

    def _identify_party(self, chamber):
        """
        Get the best available information on New York political party
        affiliations. Returns a dict mapping district to party for the
        given chamber.

        The formatting of this page is pretty abysmal, so apologies
        about the dirtiness of this method.
        """
        # These may need to be changed, but should be mostly constant
        NY_SEATS_IN_US_HOUSE = 27
        NY_STATE_SENATE_SEATS = 63
        NY_STATE_ASSEMBLY_SEATS = 150

        # Download the page and ingest using lxml
        MEMBER_LIST_URL = \
                'http://www.elections.ny.gov:8080/reports/rwservlet?cmdkey=nysboe_incumbnt'
        html = self.get(MEMBER_LIST_URL).text
        doc = lxml.html.fromstring(html)

        # Map district to party affiliation
        _congressional_affiliations = {}
        senate_affiliations = {}
        assembly_affiliations = {}
        district = None
        capture_district = False
        capture_party = False
        affiliation_text = \
                doc.xpath('/html/body/table/tr/td/font[@color="#0000ff"]/b/text()')
        for affiliation in affiliation_text:

            if capture_district and capture_party:
                raise AssertionError(
                        "Assembly party parsing simultaneously looking for "
                        "both district number and party name"
                        )

            # Remove non-breaking space characters
            affiliation = re.sub(r'\xa0', ' ', affiliation)

            # Ignore the header text when parsing
            try:
                datetime.datetime.strptime(affiliation, "%B %d, %Y")
                is_date = True
            except ValueError:
                is_date = False
            if is_date or \
                    affiliation == "Elected Representatives for New York State by Office and District":
                pass

            # Otherwise, check to see if a District or Party is indicated
            elif affiliation == u'District : ':
                capture_district = True
            elif affiliation == u'Party : ':
                capture_party = True

            # If a search has been initiated for District or Party, then capture them
            elif capture_district:
                district = affiliation
                assert district, "No district found"
                capture_district = False
            elif capture_party:
                # Skip capturing of members who are at-large, such as governor
                if not district:
                    capture_party = False
                    continue

                assert affiliation, "No party is indicated for district {}".format(district)

                # Congressional districts are listed first, then state
                # senate, then assembly
                # If a repeat district is seen, assume it's from the
                # next body in that list
                if (not _congressional_affiliations.get(district) and
                        int(district) <= NY_SEATS_IN_US_HOUSE):
                    _congressional_affiliations[district] = affiliation.title()
                elif (not senate_affiliations.get(district) and
                        int(district) <= NY_STATE_SENATE_SEATS):
                    senate_affiliations[district] = affiliation.title()
                elif (not assembly_affiliations.get(district) and
                        int(district) <= NY_STATE_ASSEMBLY_SEATS):
                    assembly_affiliations[district] = affiliation.title()
                else:
                    raise AssertionError(
                            "District {} appears too many times in party document".
                            format(district)
                            )

                district = None
                capture_party = False

            else:
                raise AssertionError(
                        "Assembly party parsing found inappropriate text: "
                        "'{}'".format(affiliation)
                        )

        if chamber == 'upper':
            return senate_affiliations
        elif chamber == 'lower':
            return assembly_affiliations
        else:
            raise AssertionError("Unknown chamber passed to party parser")

    def _parse_office(self, office_node):
        """
        Gets the contact information from the provided office.
        """
        office_name_text = self._get_node(
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
        street_address_text = self._get_node(
            office_node,
            './/div[@class="street-address"][1]/'
            'span[@itemprop="streetAddress"][1]/text()')

        if street_address_text is not None:
            street_address = street_address_text.strip()

        # Get office city.
        city_text = self._get_node(
            office_node,
            './/span[@class="locality"][1]/text()')

        if city_text is not None:
            city = city_text.strip()

        # Get office state.
        state_text = self._get_node(
            office_node,
            './/span[@class="region"][1]/text()')

        if state_text is not None:
            state = state_text.strip()

        # Get office postal code.
        zip_code_text = self._get_node(
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
        phone_node = self._get_node(
            office_node,
            './/div[@class="tel"]/span[@itemprop="telephone"]')

        if phone_node is not None:
            phone = phone_node.text.strip()

        # Get office fax number.
        fax_node = self._get_node(
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

    def _get_node(self, base_node, xpath_query):
        """
        Attempts to return only the first node found for an xpath query. Meant
        to cut down on exception handling boilerplate.
        """
        try:
            node = base_node.xpath(xpath_query)[0]
        except IndexError:
            node = None

        return node

    def _get_nodes(self, base_node, xpath_query):
        """
        Attempts to return all nodes found for an xpath query. Meant to cut
        down on exception handling boilerplate.
        """
        try:
            nodes = base_node.xpath(xpath_query)
        except IndexError:
            nodes = None

        return nodes

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber + '_chamber')(term)

    def scrape_upper_chamber(self, term):
        """
        Finds legislators from the upper chamber of the NY senate.
        """
        url = 'http://www.nysenate.gov/senators-committees'

        page = self.lxmlize(url)

        legislator_nodes = page.xpath(
            '//div[contains(@class, "u-even") or contains(@class, "u-odd")]/a')

        for legislator_node in legislator_nodes:
            legislator_url = legislator_node.attrib['href']

            # Find element containing senator data.
            info_node = self._get_node(
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
            name_node = self._get_node(
                info_node,
                'h4[@class="nys-senator--name"]')

            if name_node is not None:
                name = name_node.text.strip()
            else:
                # Skip the legislator if a name cannot be found.
                continue

            # Find legislator's district number.
            district_node = self._get_node(
                info_node,
                './/span[@class="nys-senator--district"]')

            if district_node is not None:
                district_text = district_node.xpath('.//text()')[2]
                district = re.sub(r'\D', '', district_text)

            # Find legislator's party affiliation.
            party_node = self._get_node(
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
            photo_node = self._get_node(
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
        email_node = self._get_node(
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
        office_nodes = self._get_nodes(
            legislator_page,
            '//div[@class="adr"]')

        for office_node in office_nodes:
            office = self._parse_office(office_node)

            if office is not None:
                legislator.add_office(**office)

    def scrape_lower_chamber(self, term):
        url = "http://assembly.state.ny.us/mem/?sh=email"
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        # full_names = []

        def _split_list_on_tag(lis, tag):
            data = []
            for entry in lis:
                if entry.attrib['class'] == tag:
                    yield data
                    data = []
                else:
                    data.append(entry)

        party_by_district = self._identify_party('lower')

        for row in _split_list_on_tag(page.xpath(
                "//div[@id='maincontainer']/div[contains(@class, 'email')]"),
                "emailclear"
                ):

            try:
                name, district, email = row
            except ValueError:
                name, district = row
                email = None

            link = name.xpath(".//a[contains(@href, '/mem/')]")
            if link != []:
                link = link[0]
            else:
                link = None

            if email is not None:
            # XXX: Missing email from a record on the page
            # as of 12/11/12. -- PRT
                email = email.xpath(".//a[contains(@href, 'mailto')]")
                if email != []:
                    email = email[0]
                    email = email.text_content().strip()
                else:
                    email = None

            name = link.text.strip()
            if name == 'Assembly Members':
                continue

            # empty seats
            if 'Assembly District' in name:
                continue

            district = link.xpath("string(../following-sibling::"
                                  "div[@class = 'email2'][1])")
            district = district.rstrip('rthnds')

            party = party_by_district[district].strip()

            photo_url = "http://assembly.state.ny.us/mem/pic/%03d.jpg" % \
                    int(district)
            leg_url = link.get('href')

            legislator = Legislator(term, 'lower', district, name,
                                    party=party,
                                    url=leg_url,
                                    photo_url=photo_url)
            legislator.add_source(url)

            # Legislator
            self.scrape_lower_offices(leg_url, legislator, email)

            self.save_legislator(legislator)

    def scrape_lower_offices(self, url, legislator, email=None):
        legislator.add_source(url)

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        offices = False

        for data in doc.xpath('//div[@class="officehdg"]'):
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
