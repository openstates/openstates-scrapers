import re
import lxml
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin, validate_email_address


class OKLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ok'
    latest_only = True

    _parties = {'R': 'Republican', 'D': 'Democratic'}

    def _scrub(self, text):
        """Squish whitespace and kill \xa0."""
        return re.sub(r'[\s\xa0]+', ' ', text)

    def _clean_office_info(self, office_info):
        office_info = map(self._scrub, office_info.itertext())
        # Throw away anything after any email address, phone number, or
        # address lines.
        while office_info:
            last = office_info[-1]
            if '@' not in last \
                and ', OK' not in last \
                and not re.search(r'[\d\-\(\) ]{7,}', last):
                office_info.pop()
            else:
                break
        return office_info

    def _extract_phone(self, office_info):
        phone = None

        for line in office_info:
            phone_match = re.search(r'''(\(\d{3}\) \d{3}-\d{4}|
                \d{3}.\d{3}.\d{4})''', line)
            if phone_match is not None:
                phone = phone_match.group(1).strip()

        return phone

    def _extract_email(self, doc):
        xpath = '//div[@class="districtheadleft"]' \
                + '/b[contains(text(), "Email:")]' \
                + '/../following-sibling::div' \
                + '/script/text()'
        script = doc.xpath(xpath)[0]
        line = filter(
            lambda line: '+ "@" +' in line,
            script.split('\r\n'))[0]
        parts = re.findall(r'"(.+?)"', line)

        email = ''.join(parts)

        return email if validate_email_address(email) else None


    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber + '_chamber')(term)

    def scrape_lower_chamber(self, term):
        url = "http://www.okhouse.gov/Members/Default.aspx"

        page = self.lxmlize(url)

        legislator_nodes = self.get_nodes(
            page,
            '//table[@id="ctl00_ContentPlaceHolder1_RadGrid1_ctl00"]/tbody/tr')

        for legislator_node in legislator_nodes:
            name_node = self.get_node(
                legislator_node,
                './/td[1]/a')

            if name_node is not None:
                name_text = name_node.text.strip()

                last_name, delimiter, first_name = name_text.partition(',')

                if last_name is not None and first_name is not None:
                    first_name = first_name.strip()
                    last_name = last_name.strip()
                    name = ' '.join([first_name, last_name])
                else:
                    raise ValueError('Unable to parse name: {}'.format(
                        name_text))

                if name.startswith('House District'):
                    continue

            district_node = self.get_node(
                legislator_node,
                './/td[3]')

            if district_node is not None:
                district = district_node.text.strip()

            party_node = self.get_node(
                legislator_node,
                './/td[4]')

            if party_node is not None:
                party_text = party_node.text.strip()

            party = self._parties[party_text]

            legislator_url = 'http://www.okhouse.gov/District.aspx?District=' + district

            legislator_page = self.lxmlize(legislator_url)

            photo_url = self.get_node(
                legislator_page,
                '//a[@id="ctl00_ContentPlaceHolder1_imgHiRes"]/@href')

            legislator = Legislator(
                _scraped_name=name_text,
                full_name=name,
                term=term,
                chamber='lower',
                district=district,
                party=party,
                photo_url=photo_url,
                url=legislator_url
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

            # Get the email address, extracted from a series of JS
            # "document.write" lines.
            email = self._extract_email(doc)
            legislator['email'] = email

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

        for a in doc.xpath('//table[@summary]')[0].xpath('.//td//a[contains(@href, "biographies")]'):
            tail = a.xpath('..')[0].tail
            if tail:
                district = tail.split()[1]
            else:
                district = a.xpath('../../span')[1].text.split()[1]

            if a.text == None:
                self.warning("District {} appears to be empty".format(district))
                continue
            else:
                match = re.match(r'(.+) \(([A-Z])\)', a.text.strip())
                name, party = match.group(1), self._parties[match.group(2)]

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
        lxml.etree.strip_tags(col1, 'sup')
        lxml.etree.strip_tags(col2, 'sup')

        capitol_office_info = self._clean_office_info(col1)

        # Set email on the leg object.
        if '@' in capitol_office_info[-1]:
            email = capitol_office_info.pop()
            legislator['email'] = email
        else:
            email = None

        capitol_phone = self._extract_phone(capitol_office_info)

        capitol_address_lines = map(
            lambda line: line.strip(),
            filter(
                lambda string: re.search(r', OK|Lincoln Blvd|Room \d', string),
                capitol_office_info))

        office = dict(
            name='Capitol Office',
            type='capitol',
            address='\n'.join(capitol_address_lines),
            fax=None,
            email=email,
            phone=capitol_phone)

        legislator.add_office(**office)

        district_office_info = self._clean_office_info(col2)

        # This probably isn't a valid district office at less than two lines.
        if len(district_office_info) < 2:
            return

        district_address_lines = []
        for line in district_office_info:
            district_address_lines.append(line.strip())
            if 'OK' in line:
                break

        if 'OK' in district_address_lines[-1]:
            district_address = '\n'.join(filter(lambda line: line,
                district_address_lines))
        else:
            district_address = None
        #self.logger.debug(district_address)

        district_phone = self._extract_phone(district_office_info)

        office = dict(
            name='District Office',
            type='district',
            address=district_address,
            fax=None,
            email=None,
            phone=district_phone)

        legislator.add_office(**office)
