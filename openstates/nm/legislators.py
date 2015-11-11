import re
import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class NMLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'nm'

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

    def validate_phone_number(self, phone_number):
        is_valid = False

        # Phone format validation regex.
        phone_pattern = re.compile(r'\(?\d{3}\)?\s?-?\d{3}-?\d{4}')
        phone_match = phone_pattern.match(phone_number)
        if phone_match is not None:
            is_valid = True

        return is_valid

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        # Xpath query string format for legislative chamber.
        base_xpath = '//table[@id="ctl00_mainCopy_gridView{}Districts"]'\
            '//a[contains(@href, "SPONCODE")]/@href'

        if chamber == 'lower':
            chamber_xpath = base_xpath.format('House')
        elif chamber == 'upper':
            chamber_xpath = base_xpath.format('Senate')

        url = 'http://www.nmlegis.gov/lcs/districts.aspx'

        page = self.lxmlize(url)

        legislator_urls = self._get_nodes(
            page,
            chamber_xpath)

        for legislator_url in legislator_urls:
            # Indicators used for empty seats.
            vacancy_strings = ('SNULL', 'SPONCODE=HVACA')
            if any(x in legislator_url for x in vacancy_strings):
                self.logger.info('Skipping vacant seat.')
                continue
            self.scrape_legislator(chamber, term, legislator_url)

    def scrape_legislator(self, chamber, term, url):
        # Initialize default values for legislator attributes.
        full_name        = None
        party            = None
        photo_url        = None
        email            = None
        capitol_address  = None
        capitol_phone    = None
        district_address = None
        district_phone   = None

        # Xpath query string format for legislator information nodes.
        xpath = './/span[@id="ctl00_mainCopy_formViewLegislator_{}"]'

        page = self.lxmlize(url)

        info_node = self._get_node(
            page,
            '//table[@id="ctl00_mainCopy_formViewLegislator"]')
        if info_node is None:
            raise ValueError('Could not locate legislator data.')

        district_node = self._get_node(
            info_node,
            './/a[@id="ctl00_mainCopy_formViewLegislator_linkDistrict"]')
        if district_node is not None:
            district = district_node.text.strip()

        header_node = self._get_node(
            info_node,
            xpath.format('lblHeader'))
        if header_node is not None:
            full_name, party = header_node.text.strip().rsplit('-', 1)
            full_name = full_name.replace('Representative', '').replace(
                'Senator', '').strip()

        if '(D)' in party:
            party = 'Democratic'
        elif '(R)' in party:
            party = 'Republican'
        elif '(DTS)' in party:
            # decline to state = independent
            party = 'Independent'
        else:
            raise AssertionError('Unknown party {} for {}'.format(
                party,
                full_name))

        photo_url = self._get_node(
            info_node,
            './/img[@id="ctl00_mainCopy_formViewLegislator_imgLegislator"]/@src')

        email_node = self._get_node(
            info_node,
            './/a[@id="ctl00_mainCopy_formViewLegislator_linkEmail"]')
        if email is not None:
            email = email_node.text.strip()

        capitol_address_node = self._get_node(
            info_node,
            xpath.format('lblCapitolRoom'))
        if capitol_address_node is not None:
            capitol_address_text = capitol_address_node.text
            if capitol_address_text is not None:
                capitol_address = 'Room {} State Capitol\nSanta Fe, NM 87501'\
                    .format(capitol_address_text.strip())

        capitol_phone_node = self._get_node(
            info_node,
            xpath.format('lblCapitolPhone'))
        if capitol_phone_node is not None:
            capitol_phone_text = capitol_phone_node.text
            if capitol_phone_text is not None:
                capitol_phone_text = capitol_phone_text.strip()
                if self.validate_phone_number(capitol_phone_text):
                    capitol_phone = capitol_phone_text

        district_address_node = self._get_node(
            info_node,
            xpath.format('lblAddress'))
        if district_address_node is not None:
            district_address = '\n'.join(district_address_node.text.strip())

        district_phone_node = self._get_node(
            info_node,
            xpath.format('lblHomePhone'))
        if district_phone_node is not None:
            district_phone_text = district_phone_node.text
            if district_phone_text is not None:
                district_phone_text = district_phone_text.strip()
                if self.validate_phone_number(district_phone_text):
                    district_phone = district_phone_text

        legislator = Legislator(
            term=term,
            chamber=chamber,
            district=district,
            full_name=full_name,
            party=party,
            photo_url=photo_url)
        legislator.add_source(url)

        legislator.add_office(
            'district',
            'District Office',
            address=district_address,
            phone=district_phone)
        legislator.add_office(
            'capitol',
            'Capitol Office',
            address=capitol_address,
            phone=capitol_phone,
            email=email)

        committees_nodes = self._get_nodes(
            info_node,
            '//table[@id="ctl00_mainCopy_gridViewCommittees"]/tr')

        # First row node should contain header - skip.
        for committee_node in committees_nodes[1:]:
            role, committee, note = [x.text_content() for x in committee_node\
                .xpath('./td')]
            committee = committee.title()
            if 'Interim' in note:
                role = 'interim ' + role.lower()
            else:
                role = role.lower()
            if ' Committee' in committee:
                committee = committee.replace(" Committee", '')
            if ' Subcommittee' in committee:
                committee = committee.replace(' Subcommittee', '')
            legislator.add_role(
                'committee member',
                term,
                committee=committee,
                position=role,
                chamber=chamber)

        self.save_legislator(legislator)
