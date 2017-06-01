# -*- coding: utf-8 -*-
import lxml.html
import re
import unicodedata
import scrapelib
from pupa.scrape import Person, Scraper
from openstates.utils import LXMLMixin


class PRPersonScraper(Scraper, LXMLMixin):

    def validate_phone_number(self, phone_number):
        is_valid = False

        # Phone format validation regex.
        phone_pattern = re.compile(r'\(?\d{3}\)?\s?-?\d{3}-?\d{4}')
        phone_match = phone_pattern.match(phone_number)
        if phone_match is not None:
            is_valid = True

        return is_valid

    def scrape(self, chamber=None):
        term = self.jurisdiction.legislative_sessions[-1]['identifier']
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from getattr(self, 'scrape_' + chamber + '_chamber')(term)

    def scrape_upper_chamber(self, term):
        urls = {
            'At-Large': 'http://www.senadopr.us/Pages/SenadoresporAcumulacion.aspx',
            'I': 'http://www.senadopr.us/Pages/Senadores%20Distrito%20I.aspx',
            'II': 'http://www.senadopr.us/Pages/Senadores%20Distrito%20II.aspx',
            'III': 'http://www.senadopr.us/Pages/Senadores%20Distrito%20III.aspx',
            'IV': 'http://www.senadopr.us/Pages/Senadores%20Distrito%20IV.aspx',
            'V': 'http://www.senadopr.us/Pages/Senadores%20Distrito%20V.aspx',
            'VI': 'http://www.senadopr.us/Pages/Senadores%20Distrito%20VI.aspx',
            'VII': 'http://www.senadopr.us/Pages/Senadores%20Distrito%20VII.aspx',
            'VIII': 'http://www.senadopr.us/Pages/Senadores%20Distrito%20VIII.aspx'
        }

        for district, url in urls.items():
            leg_page_html = self.get(url).text
            doc = lxml.html.fromstring(leg_page_html)
            doc.make_links_absolute(url)
            rows = doc.xpath('//table[@summary="Senadores 2013-2016"]'
                             '/tr[not(@class="ms-viewheadertr")]')

            for row in rows:
                tds = row.xpath('td')

                name = tds[0].text_content().title().replace('Hon.', '', 1).strip()
                party = tds[1].text_content()
                phone = tds[2].text_content()
                email = tds[3].text_content()

                # Code to guess the picture
                # Those middle names abbreviations are sometimes weird.
                namefixed = str(name.replace(".", ". "))
                # Remove the accents
                namefixed = unicodedata.normalize('NFKD', namefixed).encode('ascii', 'ignore')
                nameparts = namefixed.split()
                if nameparts[1].endswith('.'):
                    lastname = nameparts[2]
                else:
                    lastname = nameparts[1]

                # Construct the photo url
                photo_url = 'http://www.senadopr.us/Fotos%20Senadores/sen_' + \
                            (nameparts[0][0] + lastname).lower() + '.jpg'
                try:
                    self.head(photo_url)  # Checking to see if the file is there
                except scrapelib.HTTPError:         # If not, leave out the photo_url
                    photo_url = ''

                person = Person(primary_org='upper',
                                district=district,
                                name=name,
                                party=party,
                                image=photo_url)
                if email:
                    person.add_contact_deatil(type='email',
                                              value=email,
                                              note='Capitol Office')
                if phone:
                    person.add_contact_deatil(type='voice',
                                              value=phone,
                                              note='Capitol Office')
                person.add_link(url)
                person.add_source(url)

                yield person

    def scrape_lower_chamber(self, term):
        # E-mail contact is now hidden behind webforms. Sadness.

        party_map = {'PNP': 'Partido Nuevo Progresista',
                     'PPD': u'Partido Popular Democr\xe1tico',
                     'PIP': u'Partido Independentista Puertorrique\u00F1o',
                     }

        url = 'http://www.tucamarapr.org/dnncamara/ComposiciondelaCamara.aspx'

        page = self.lxmlize(url)

        member_nodes = self.get_nodes(
            page,
            '//div[@class="info-block"][1]//a[@class="opener"]')

        if member_nodes is not None:
            for member_node in member_nodes:
                # Initialize default values for legislator attributes.
                name = None
                district = None
                address = None
                party = None
                photo_url = None
                phone = None
                fax = None

                photo_url = self.get_node(
                    member_node,
                    './/span[@class="identity"]/img/@src')

                # Node reference for convenience.
                info_node = self.get_node(
                    member_node,
                    './/span[@class="info"]')

                name_node = self.get_node(
                    info_node,
                    './/span[@class="name"]')
                # Strip titles from legislator name.
                if name_node is not None:
                    name_text = name_node.text.strip()
                    name_text = re.sub(r'^Hon\.[\s]*', '', name_text)
                    name_text = re.sub(r' - .*$', '', name_text)
                    name = ' '.join(name_text.split())

                party_node = self.get_node(
                    info_node,
                    './/span[@class="party"]/span')
                if party_node is not None:
                    party_text = party_node.text.strip()
                    party = party_map[party_text]

                district_node = self.get_node(
                    info_node,
                    './/span[@class="district"]')
                if district_node is not None:
                    district_text = district_node.text.strip()

                    try:
                        # district_number = re.search(r'0?(\d{1,2})',
                        #                            district_text).group(1)
                        district = re.sub(r'^Distrito[\s]*', '',
                                          district_text).strip()
                    except AttributeError:
                        if "Distrito" not in district_text:
                            district = 'At-Large'
                        else:
                            warning = u'{} missing district number.'
                            self.warning(warning.format(name))

                address_node = self.get_node(
                    info_node,
                    './/span[@class="address"]')
                if address_node is not None:
                    address_text = address_node.text
                    if address_text and not address_text.isspace():
                        address = address_text.strip()

                # Only grabs the first validated phone number found.
                # Typically, representatives have multiple phone numbers.
                phone_nodes = self.get_nodes(
                    member_node,
                    './/span[@class="two-columns"]//span[@class="data-type"'
                    'and contains(text(), "Tel:")]')
                if phone_nodes is not None:
                    has_valid_phone = False

                    for phone_node in phone_nodes:
                        # Don't keep searching phone numbers if a good
                        # one is found.
                        if has_valid_phone:
                            break

                        phone_text = phone_node.text
                        phone_text = re.sub(r'^Tel:[\s]*', '', phone_text)\
                            .strip()
                        if self.validate_phone_number(phone_text):
                            phone = phone_text
                            has_valid_phone = True

                fax_node = self.get_node(
                    member_node,
                    './/span[@class="two-columns"]//span[@class="data-type"'
                    ' and contains(text(), "Fax:")]')
                if fax_node is not None:
                    fax_text = fax_node.text
                    fax_text = re.sub(r'^Fax:[\s]*', '', fax_text).strip()
                    if self.validate_phone_number(fax_text):
                        fax = fax_text

                person = Person(primary_org='lower',
                                district=district,
                                name=name,
                                party=party,
                                image=photo_url)

                person.add_link(url)
                person.add_source(url)

                if address:
                    person.add_contact_deatil(type='address',
                                              value=address,
                                              note='capitol Office')
                if phone:
                    person.add_contact_deatil(type='voice',
                                              value=phone,
                                              note='capitol Office')
                if fax:
                    person.add_contact_deatil(type='fax',
                                              value=fax,
                                              note='capitol Office')

                yield person
