from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import re
import unicodedata
import scrapelib

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
                                             party=party, phone=phone,
                                             email=email, url=url, 
                                             photo_url=picture_filename)

                    except scrapelib.HTTPError:         # If not, leave out the photo_url
                        leg = Legislator(term, 'upper', district, name,
                                         party=party, phone=phone, email=email,
                                         url=url)

                    leg.add_source(url)
                    self.save_legislator(leg)

    def scrape_house(self, term):
        url = 'http://www.camaraderepresentantes.org/cr_legs.asp'

        party_map = {'PNP': 'Partido Nuevo Progresista',
                     'PPD': u'Partido Popular Democr\xe1tico'}

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)
            tables = doc.xpath('//table[@class="img_news"]')

            # first table is district-based, second is at-large
            for table, at_large in zip(tables, [False, True]):
                # skip last td in each table
                for td in table.xpath('.//td')[:-1]:
                    photo_url = td.xpath('.//img/@src')[0]
                    
                    # for these we can split names and get district
                    if not at_large:
                        name, district = td.xpath('.//b/text()')
                        first_name, last_name = name.split(u'\xa0 ')
                        name = '%s %s' % (first_name, last_name)
                        district = district.rsplit(' ', 1)[-1]
                    else:
                        name = td.xpath('.//b/text()')[0]
                        district = 'At-Large'   #for at large districts
                        first_name = last_name = ''

                    party = party_map[td.xpath('.//font')[1].text_content()]

                    leg = Legislator(term, 'lower', district, name,
                                     first_name=first_name,
                                     last_name=last_name,
                                     party=party,
                                     photo_url=photo_url)
                    leg.add_source(url)
                    self.save_legislator(leg)
