import re
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin

base_url = 'http://www.nmlegis.gov/Members/Legislator_List'


def extract_phone_number(phone_number):
    phone_pattern = re.compile(r'(\(?\d{3}\)?\s?-?)?(\d{3}-?\d{4})')
    return phone_pattern.search(phone_number).groups()


class NMLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'nm'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            query = '?T=S'
        elif chamber == 'lower':
            query = '?T=R'

        self.logger.info('Scraping {} {} chamber.'.format(
            self.jurisdiction.upper(),
            chamber))

        url = '{0}{1}'.format(base_url, query)

        page = self.lxmlize(url)

        # Xpath query string format for legislator links.
        base_xpath = (
            '//a[contains(@id, '
            '"MainContent_listViewLegislators_linkLegislatorPicture")]/@href')

        legislator_urls = self.get_nodes(page, base_xpath)

        for legislator_url in legislator_urls:
            # Indicators used for empty seats.
            vacancy_strings = ('SNULL', 'SPONCODE=HVACA')
            if any(x in legislator_url for x in vacancy_strings):
                self.logger.info('Skipping vacant seat.')
                continue
            self.scrape_legislator(chamber, term, legislator_url)

    def scrape_legislator(self, chamber, term, url):
        # Initialize default values for legislator attributes.
        full_name = None
        party = None
        photo_url = None
        email = None
        capitol_address = None
        capitol_phone = None
        district = None
        district_address = None
        district_phone = None

        if chamber == 'upper':
            title_prefix = 'Senator '
        elif chamber == 'lower':
            title_prefix = 'Representative '
        else:
            title_prefix = ''

        santa_fe_area_code = '(505)'

        page = self.lxmlize(url)

        name_node = self.get_node(
            page,
            './/span[@id="MainContent_formViewLegislatorName'
            '_lblLegislatorName"]')

        if name_node is not None:
            n_head, n_sep, n_party = name_node.text.rpartition(' - ')

            full_name = re.sub(r'^{}'.format(title_prefix), '', n_head.strip())

            if '(D)' in n_party:
                party = 'Democratic'
            elif '(R)' in n_party:
                party = 'Republican'
            elif '(DTS)' in n_party:
                # decline to state = independent
                party = 'Independent'
            else:
                raise AssertionError('Unknown party {} for {}'.format(
                    party,
                    full_name))

        info_node = self.get_node(
            page,
            '//table[@id="MainContent_formViewLegislator"]')
        if info_node is None:
            raise ValueError('Could not locate legislator data.')

        photo_node = self.get_node(
            info_node,
            './/img[@id="MainContent_formViewLegislator_imgLegislator"]')
        if photo_node is not None:
            photo_url = photo_node.get('src')

        district_node = self.get_node(
            info_node,
            './/a[@id="MainContent_formViewLegislator_linkDistrict"]')
        if district_node is not None:
            district = district_node.text.strip()

        email_node = self.get_node(
            info_node,
            './/a[@id="MainContent_formViewLegislator_linkEmail"]')
        if email_node is not None and email_node.text:
            email = email_node.text.strip()

        capitol_address_node = self.get_node(
            info_node,
            './/span[@id="MainContent_formViewLegislator_lblCapitolRoom"]')
        if capitol_address_node is not None:
            capitol_address_text = capitol_address_node.text
            if capitol_address_text is not None:
                capitol_address = 'Room {} State Capitol\nSanta Fe, NM 87501'\
                    .format(capitol_address_text.strip())

        capitol_phone_node = self.get_node(
            info_node,
            './/span[@id="MainContent_formViewLegislator_lblCapitolPhone"]')
        if capitol_phone_node is not None:
            capitol_phone_text = capitol_phone_node.text
            if capitol_phone_text:
                capitol_phone_text = capitol_phone_text.strip()
                area_code, phone = extract_phone_number(capitol_phone_text)
                if phone:
                    capitol_phone = '{} {}'.format(
                        area_code.strip() if area_code else santa_fe_area_code,
                        phone)

        district_address_node = self.get_node(
            info_node,
            './/span[@id="MainContent_formViewLegislator_lblAddress"]')
        if district_address_node is not None:
            district_address = '\n'.join(district_address_node.xpath("text()"))

        office_phone_node = self.get_node(
            info_node,
            './/span[@id="MainContent_formViewLegislator_lblOfficePhone"]')

        home_phone_node = self.get_node(
            info_node,
            './/span[@id="MainContent_formViewLegislator_lblHomePhone"]')

        if office_phone_node is not None and office_phone_node.text:
            district_phone_text = office_phone_node.text
        elif home_phone_node is not None and home_phone_node.text:
            district_phone_text = home_phone_node.text
        else:
            district_phone_text = None
        if district_phone_text:
            d_area_code, d_phone = extract_phone_number(district_phone_text)
            district_phone = '{} {}'.format(d_area_code.strip(), d_phone)

        legislator = Legislator(
            term=term,
            chamber=chamber,
            district=district,
            full_name=full_name,
            party=party,
            photo_url=photo_url)

        if email:
            legislator['email'] = email

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

        self.save_legislator(legislator)
