# -*- coding: utf-8 -*-
from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin

import lxml.html
import re
import unicodedata
import scrapelib

PHONE_RE = re.compile('\(?\d{3}\)?\s?-?\d{3}-?\d{4}')

class PRLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'pr'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            self.scrape_senate(term)
        elif chamber == 'lower':
            self.scrape_house(term)

    def scrape_senate(self, term):
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
            leg_page_html = self.urlopen(url)
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
                    picture_data = self.urlopen(photo_url)  # Checking to see if the file is there
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

    def scrape_house(self, term):
        party_map = {'PNP': 'Partido Nuevo Progresista',
                     'PPD': u'Partido Popular Democr\xe1tico'}

        url = 'http://www.camaraderepresentantes.org/cr_legs.asp'
        doc = self.lxmlize(url)

        members = doc.xpath('//table[@class="img_news"]/tr/td[*]')
        for member in members:

            (member_url, ) = member.xpath('a/@href')
            (name, ) = member.xpath('font/b/text()[1]')
            name = " ".join(name.split())
            (photo_url, ) = member.xpath('a/img/@src')
            party = party_map[member.xpath('font//font/text()')[0]]

            member_text = member.text_content()
            missing_district_on_index_page = False
            try:
                district = re.search(r'0?(\d{1,2})', member_text).group(1)
            except AttributeError:
                if "Distrito" not in member_text:
                    district = 'At-Large'
                else:
                    self.warning(u"{} represents a district, but it is not listed".
                            format(name))
                    missing_district_on_index_page = True

                    # Special-case one member, whose page only displays a SQL error
                    if name == u"Yashira M. Lebrón Rodríguez":
                        leg = Legislator(
                                term=term,
                                chamber='lower',
                                district='8',
                                full_name=name,
                                party=party
                                )
                        leg.add_source(url)
                        self.save_legislator(leg)

                        special_case_still_needed = True
                        continue

            # Parse the member's webpage for contact information
            member_doc = self.lxmlize(member_url)

            (email, ) = member_doc.xpath('//a[starts-with(@href, "mailto:")]/text()')
            phone_and_fax = [
                    x.strip() for x in
                    member_doc.xpath(u'//b[contains(text(), "Teléfono(s):")]/..//text()')
                    if x.strip()
                    ]
            try:
                phone_index = phone_and_fax.index(u"Teléfono(s):") + 1
                phone = phone_and_fax[phone_index]
            except IndexError:
                phone = None
            try:
                fax_index = phone_and_fax.index(u"Fax:") + 1
                fax = phone_and_fax[fax_index]
            except ValueError:
                fax = None

            if missing_district_on_index_page:
                (district, ) = member_doc.xpath('//div[@class="tbrown"]/span/b/text()')
                district = re.search(r'Distrito 0?(\d{1,2})', district).group(1)

            leg = Legislator(
                    term=term,
                    chamber='lower',
                    district=district,
                    full_name=name,
                    party=party,
                    photo_url=photo_url
                    )

            leg.add_source(url)
            leg.add_source(member_url)
            leg.add_office(
                    type='capitol',
                    name='Oficina del Capitolio',
                    phone=phone,
                    fax=fax,
                    email=email
                    )

            self.save_legislator(leg)

        assert special_case_still_needed, "Lebrón Rodríguez's page is no longer broken; remove special-casing"
