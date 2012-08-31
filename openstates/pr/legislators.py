from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import re
import unicodedata
import scrapelib

PHONE_RE = re.compile('\(?\d{3}\)?\s?-?\d{3}-?\d{4}')

class PRLegislatorScraper(LegislatorScraper):
    state = 'pr'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            self.scrape_senate(term)
        elif chamber == 'lower':
            self.scrape_house(term)

    def scrape_senate(self, term):
        urls = (
         'http://www.senadopr.us/senadores/Pages/Senadores%20Acumulacion.aspx',
         'http://www.senadopr.us/Pages/Senadores%20Distrito%20I.aspx',
         'http://www.senadopr.us/Pages/Senadores%20Distrito%20II.aspx',
         'http://www.senadopr.us/Pages/Senadores%20Distrito%20III.aspx',
         'http://www.senadopr.us/Pages/Senadores%20Distrito%20IV.aspx',
         'http://www.senadopr.us/Pages/Senadores%20Distrito%20V.aspx',
         'http://www.senadopr.us/Pages/Senadores%20Distrito%20VI.aspx',
         'http://www.senadopr.us/Pages/Senadores%20Distrito%20VII.aspx',
         'http://www.senadopr.us/Pages/Senadores%20Distrito%20VIII.aspx')

        for counter, url in enumerate(urls):
            with self.urlopen(url) as leg_page_html:
                doc = lxml.html.fromstring(leg_page_html)
                doc.make_links_absolute(url)
                table = doc.xpath('//table[@summary="Listado de Senadores"]')[0]

                # skip first row
                for row in table.xpath('tr')[1:]:
                    tds = row.xpath('td')

                    name = tds[0].text_content().title().replace('Hon.','',1).strip()
                    party = tds[1].text_content()
                    phone = tds[2].text_content()
                    email = tds[3].text_content()
                    #shapefiles denote 0 as At-Large Districts
                    if counter == 0:
                        district = 'At-Large'
                    else:
                        district = str(counter)

                    #Code to guess the picture
                    namefixed = unicode(name.replace(".",". "))  #Those middle names abbreviations are sometimes weird.
                    namefixed = unicodedata.normalize('NFKD', namefixed).encode('ascii', 'ignore') #Remove the accents
                    nameparts = namefixed.split()
                    if nameparts[1].endswith('.'):
                        lastname = nameparts[2]
                    else:
                        lastname = nameparts[1]

                    # Construct the photo url
                    picture_filename = 'http://www.senadopr.us/Fotos%20Senadores/sen_' + (nameparts[0][0] + lastname).lower() + '.jpg'

                    try:
                        with self.urlopen(picture_filename) as picture_data:  # Checking to see if the file is there
                            leg = Legislator(term, 'upper', district, name,
                                             party=party,
                                             email=email, url=url,
                                             photo_url=picture_filename)

                    except scrapelib.HTTPError:         # If not, leave out the photo_url
                        leg = Legislator(term, 'upper', district, name,
                                         party=party, phone=phone, email=email,
                                         url=url)

                    leg.add_office('capitol', 'Oficina del Capitolio',
                                   phone=phone)
                    leg.add_source(url)
                    self.save_legislator(leg)

    def scrape_house(self, term):
        url = 'http://www.camaraderepresentantes.org/cr_legs.asp'

        party_map = {'PNP': 'Partido Nuevo Progresista',
                     'PPD': u'Partido Popular Democr\xe1tico'}

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)
            tables = doc.xpath('//table[@width="90%"]')

            # first table is district-based, second is at-large
            for table, at_large in zip(tables, [False, True]):

                for tr in table.xpath('.//tr')[1:]:
                    tds = tr.getchildren()
                    if not at_large:
                        # tds: name, district, addr, phone, office, email
                        name = tds[0]
                        district = tds[1].text_content().lstrip('0')
                        capitol_office = tds[2]
                        phone = tds[3]
                        email = tds[5]
                        # district offices
                        district_office = tds[4]
                        district_addr = []
                        district_phone  = None
                        district_fax = None
                        pieces = district_office.xpath('.//text()')
                        for piece in pieces:
                            if piece.startswith('Tel'):
                                district_phone = PHONE_RE.findall(piece)[0]
                            elif piece.startswith('Fax'):
                                district_fax = PHONE_RE.findall(piece)[0]
                            else:
                                district_addr.append(piece)
                        if district_addr:
                            district_addr = ' '.join(district_addr)
                    else:
                        # name, addr, phone, email
                        name = tds[0]
                        district = 'At-Large'
                        capitol_office = tds[1]
                        phone = tds[2]
                        email = tds[3]
                        district_addr = None

                    # cleanup is same for both tables
                    name = re.sub('\s+', ' ',
                                  name.text_content().strip().replace(u'\xa0', ' '))
                    email = email.xpath('.//a/@href')[0].strip('mailto:')

                    numbers = {}
                    for b in phone.xpath('b'):
                        numbers[b.text] = b.tail.strip()

                    # capitol_office as provided is junk
                    # things like 'Basement', and '2nd Floor'

                    # urls @ http://www.camaraderepresentantes.org/legs2.asp?r=BOKCADHRTZ
                    # where random chars are tr's id
                    leg_url = 'http://www.camaraderepresentantes.org/legs2.asp?r=' + tr.get('id')

                    leg = Legislator(term, 'lower', district, name,
                                     party='unknown', email=email, url=url)
                    leg.add_office('capitol', 'Oficina del Capitolio',
                                   phone=numbers.get('Tel:') or None,
                                   # could also add TTY
                                   #tty=numbers.get('TTY:') or None,
                                   fax=numbers.get('Fax:') or None)
                    if district_addr:
                        leg.add_office('district', 'Oficina de Distrito',
                                       address=district_addr,
                                       phone=district_phone,
                                       fax=district_fax)

                    leg.add_source(url)
                    self.save_legislator(leg)
