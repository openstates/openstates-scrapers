# -*- coding: utf-8 -*-
from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin
import lxml.html
import re
import unicodedata
import scrapelib
import logging


class PRLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'pr'

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

    def _get_page(self, url):
        """
        Prepares page retrieved from URL for xpath querying.
        """
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        return page

    def scrape(self, chamber, term):
        self.logger.info('Scraping {} {} chamber.'.format(
            self.jurisdiction.upper(),
            chamber))
        self.validate_term(term, latest_only=True)
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

        member_nodes = self._get_nodes(
            page,
            '//div[@class="info-block"][1]//a[@class="opener"]')

        if member_nodes is not None:
            for member_node in member_nodes:
                # Initialize default values for legislator attributes.
                name      = None
                district  = None
                party     = None
                photo_url = None
                phone     = None
                fax       = None

                photo_url = self._get_node(
                    member_node,
                    './/span[@class="identity"]/img/@src')
    
                # Node reference for convenience.
                info_node = self._get_node(
                    member_node,
                    './/span[@class="info"]')
    
                name_node = self._get_node(
                    info_node,
                    './/span[@class="name"]')
                # Strip titles from legislator name.
                if name_node is not None:
                    name_text = name_node.text.strip()
                    name_text = re.sub(r'^Hon\.[\s]*', '', name_text)
                    name_text = re.sub(r' - .*$', '', name_text)
                    name = ' '.join(name_text.split())
    
                party_node = self._get_node(
                    info_node,
                    './/span[@class="party"]/span')
                if party_node is not None:
                    party_text = party_node.text.strip()
                    party = party_map[party_text]
    
                district_node = self._get_node(
                    info_node,
                    './/span[@class="district"]')
                if district_node is not None:
                    district_text = district_node.text.strip()

                    try:
                        district_number = re.search(r'0?(\d{1,2})',
                            district_text).group(1)
                        district = district_text
                    except AttributeError:
                        if "Distrito" not in district_text:
                            district = 'At-Large'
                        else:
                            warning = u'{} missing district number.'
                            self.logger.warning(warning.format(name))

                phone_pattern = re.compile(r'\(?\d{3}\)?\s?-?\d{3}-?\d{4}')

                # Only grabs the first validated phone number found.
                # Typically, representatives have multiple phone numbers.
                phone_nodes = self._get_nodes(
                    member_node,
                    './/span[@class="two-columns"]//span[@class="data-type" and '
                    'contains(text(), "Tel:")]')
                if phone_nodes is not None:
                    has_valid_phone = False

                    for phone_node in phone_nodes:
                        # Don't keep searching phone numbers if a good
                        # one is found.
                        if has_valid_phone:
                            break

                        phone_text = phone_node.text.strip()
                        phone_text = re.sub(r'^Tel:[\s]*', '', phone_text).strip()

                        # Phone number validation.
                        phone_match = phone_pattern.match(phone_text)
                        if phone_match is not None:
                            phone = phone_match.group(0)
                            has_valid_phone = True
    
                fax_node = self._get_node(
                    member_node,
                    './/span[@class="two-columns"]//span[@class="data-type" and '
                    'contains(text(), "Fax:")]')
                if fax_node is not None:
                    fax_text = fax_node.text.strip()
                    fax_text = re.sub(r'^Fax:[\s]*', '', fax_text).strip()

                    # Fax number validation.
                    fax_match = phone_pattern.match(fax_text)
                    if fax_match is not None:
                        fax = fax_match.group(0)
    
                leg = Legislator(
                    term=term,
                    chamber='lower',
                    district=district,
                    full_name=name,
                    party=party,
                    photo_url=photo_url
                )
    
                leg.add_source(url)
                leg.add_office(
                    type='capitol',
                    name='Oficina del Capitolio',
                    phone=phone,
                    fax=fax,
                )

                self.save_legislator(leg)
