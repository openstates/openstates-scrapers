import re
import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class OKLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ok'
    latest_only = True

    _parties = {'R': 'Republican', 'D': 'Democratic'}

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

    def _scrub(self, text):
        """Squish whitespace and kill \xa0."""
        return re.sub(r'[\s\xa0]+', ' ', text)

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber + '_chamber')(term)

    def scrape_lower_chamber(self, term):
        url = "http://www.okhouse.gov/Members/Default.aspx"

        page = self.lxmlize(url)

        legislator_nodes = self._get_nodes(
            page,
            '//table[@id="ctl00_ContentPlaceHolder1_RadGrid1_ctl00"]/tbody/tr')

        for legislator_node in legislator_nodes:
            name_node = self._get_node(
                legislator_node,
                './/td[1]/a')

            if name_node is not None:
                self.logger.debug(name_node)
                name_text = name_node.text.strip()

                last_name, delimiter, first_name = name_text.partition(',')

                if last_name is not None and first_name is not None:
                    name = ' '.join([first_name, last_name])
                else:
                    raise ValueError('Unable to parse name: {}'.format(
                        name_text))

                if name.startswith('House District'):
                    continue

            district_node = self._get_node(
                legislator_node,
                './/td[3]')

            if district_node is not None:
                district = district_node.text.strip()

            party_node = self._get_node(
                legislator_node,
                './/td[4]')

            if party_node is not None:
                party_text = party_node.text.strip()

            party = self._parties[party_text]

            legislator_url = 'http://www.okhouse.gov/District.aspx?District=' + district

            legislator_page = self.lxmlize(legislator_url)

            photo_url = self._get_node(
                legislator_page,
                '//a[contains(@href, "HiRes")]/@href')

            legislator = Legislator(
                full_name=name,
                term=term,
                chamber='lower',
                district=district,
                party=party,
                photo_url=photo_url,
            )

            legislator.add_source(url)
            legislator.add_source(legislator_url)

            # Scrape offices.
            self.scrape_lower_offices(legislator_page, legislator)

            self.save_legislator(legislator)

    def scrape_lower_offices(self, doc, legislator):

        # Capitol offices:
        xpath = '//*[contains(text(), "Capitol Address")]'
        for bold in doc.xpath(xpath):

            # Get the address.
            address_div = bold.getparent().itersiblings().next()

            # Get the room number.
            xpath = '//*[contains(@id, "CapitolRoom")]/text()'
            room = address_div.xpath(xpath)
            if room:
                parts = map(self._scrub, list(address_div.itertext()))
                parts = [x.strip() for x in parts if x.strip()]
                phone = parts.pop()
                parts = [parts[0], 'Room ' + room[0], parts[-1]]
                address = '\n'.join(parts)
            else:
                address = None
                phone = None

            if not phone:
                phone = None

            # Set the email on the legislator object.
            try:
                xpath = '//a[contains(@href, "mailto")]/@href'
                email = doc.xpath(xpath)[0][7:]
            except IndexError:
                email = None

            office = dict(
                name='Capitol Office', type='capitol', phone=phone, email=email, address=address)

            legislator.add_office(**office)

        # District offices only have address, no other information
        district_address = doc.xpath('//span[@id="ctl00_ContentPlaceHolder1_lblDistrictAddress"]/text()')
        if district_address:
            (district_city_state, ) = doc.xpath('//span[@id="ctl00_ContentPlaceHolder1_lblDistrictCity"]/text()')
            district_address = "{}\n{}".format(district_address[0], district_city_state)

            office = dict(name='District Office', type='district', address=district_address)
            legislator.add_office(**office)

    def scrape_upper_chamber(self, term):
        url = "http://oksenate.gov/Senators/Default.aspx"
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for a in doc.xpath('//table[@summary]')[1].xpath('.//td//a[contains(@href, "biographies")]'):
            tail = a.xpath('..')[0].tail
            if tail:
                district = tail.split()[1]
            else:
                district = a.xpath('../../span')[1].text.split()[1]

            if a.text == None:
                self.warning("District {} appears to be empty".format(district))
                continue
            else:
                name, party = a.text.rsplit(None, 1)

            if party == '(D)':
                party = 'Democratic'
            elif party == '(R)':
                party = 'Republican'

            url = a.get('href')

            leg = Legislator(term, 'upper', district, name.strip(), party=party, url=url)
            leg.add_source(url)
            self.scrape_upper_offices(leg, url)
            self.save_legislator(leg)

    def scrape_upper_offices(self, legislator, url):
        url = url.replace('aspx', 'html')
        html = self.get(url).text
        legislator.add_source(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        xpath = '//h3[contains(., "Office")]'
        for table in doc.xpath(xpath)[0].itersiblings():
            if table.tag == 'table':
                break
        col1, col2 = table.xpath('tr[2]/td')

        # Add the capitol office.
        col1 = map(self._scrub, col1.itertext())
        while True:
            # Throw away anything after the email address.
            last = col1[-1]
            if '@' not in last and not re.search(r'[\d\-\(\) ]{7,}', last):
                col1.pop()
            else:
                break

        # Set email on the leg object.
        email = col1.pop()
        legislator['email'] = email

        # Next line is the phone number.
        phone = col1.pop()
        office = dict(
            name='Capitol Office',
            type='capitol',
            address='\n'.join(col1),
            fax=None, email=None, phone=phone)
        legislator.add_office(**office)

        col2 = map(self._scrub, col2.itertext())
        if len(col2) < 2:
            return

        office = dict(
            name='District Office',
            type='district',
            address='\n'.join(col2),
            fax=None, email=None, phone=phone)
        legislator.add_office(**office)
