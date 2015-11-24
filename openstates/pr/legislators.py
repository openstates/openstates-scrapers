# -*- coding: utf-8 -*-
import lxml.html
import re
import unicodedata
import scrapelib
from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class PRLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'pr'

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

        self.logger.info('Scraping {} {} chamber.'.format(
            self.jurisdiction.upper(),
            chamber))

        getattr(self, 'scrape_' + chamber + '_chamber')(term)

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

        for district, url in urls.iteritems():
            leg_page_html = self.get(url).text
            doc = lxml.html.fromstring(leg_page_html)
            doc.make_links_absolute(url)
            rows = doc.xpath('//table[@summary="Senadores 2013-2016"]/tr[not(@class="ms-viewheadertr")]')

            for row in rows:
                tds = row.xpath('td')

                name = tds[0].text_content().title().replace('Hon.','',1).strip()
                party = tds[1].text_content()
                phone = tds[2].text_content()
                email = tds[3].text_content()

                #Code to guess the picture
                namefixed = unicode(name.replace(".",". "))  #Those middle names abbreviations are sometimes weird.
                namefixed = unicodedata.normalize('NFKD', namefixed).encode('ascii', 'ignore') #Remove the accents
                nameparts = namefixed.split()
                if nameparts[1].endswith('.'):
                    lastname = nameparts[2]
                else:
                    lastname = nameparts[1]

                # Construct the photo url
                photo_url = 'http://www.senadopr.us/Fotos%20Senadores/sen_' + (nameparts[0][0] + lastname).lower() + '.jpg'
                try:
                    picture_data = self.head(photo_url)  # Checking to see if the file is there
                except scrapelib.HTTPError:         # If not, leave out the photo_url
                    photo_url = ''

                leg = Legislator(
                        term=term,
                        chamber='upper',
                        district=district,
                        full_name=name,
                        party=party,
                        photo_url=photo_url
                        )
                leg.add_office('capitol', 'Oficina del Capitolio',
                               phone=phone, email=email)
                leg.add_source(url)

                self.save_legislator(leg)

    def scrape_lower_chamber(self, term):
        # E-mail contact is now hidden behind webforms. Sadness.

        party_map = {'PNP': 'Partido Nuevo Progresista',
                     'PPD': u'Partido Popular Democr\xe1tico'}

        url = 'http://www.tucamarapr.org/dnncamara/ComposiciondelaCamara.aspx'

        page = self.lxmlize(url)

        member_nodes = self.get_nodes(
            page,
            '//div[@class="info-block"][1]//a[@class="opener"]')

        if member_nodes is not None:
            for member_node in member_nodes:
                # Initialize default values for legislator attributes.
                name      = None
                district  = None
                address   = None
                party     = None
                photo_url = None
                phone     = None
                fax       = None

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
                        district_number = re.search(r'0?(\d{1,2})',
                            district_text).group(1)
                        district = re.sub(r'^Distrito[\s]*', '',
                            district_text).strip()
                    except AttributeError:
                        if "Distrito" not in district_text:
                            district = 'At-Large'
                        else:
                            warning = u'{} missing district number.'
                            self.logger.warning(warning.format(name))

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
    
                legislator = Legislator(
                    term=term,
                    chamber='lower',
                    district=district,
                    full_name=name,
                    party=party,
                    photo_url=photo_url
                )
    
                legislator.add_source(url)
                legislator.add_office(
                    type='capitol',
                    name='Oficina del Capitolio',
                    address=address,
                    phone=phone,
                    fax=fax,
                )

                self.save_legislator(legislator)
