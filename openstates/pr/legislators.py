from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import re

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
                table = doc.xpath('//table[@summary="Listado de Senadores"]')[0]

                # skip first row
                for row in table.xpath('tr')[1:]:
                    tds = row.xpath('td')
                    photo_url = row.xpath('.//img/@src')[0]
                    name = tds[1].text_content().title()
                    party = tds[2].text_content()
                    phone = tds[3].text_content()
                    email = tds[4].text_content()

                    if counter == 0:
                        district = 'At-Large'
                    else:
                        district = str(counter)

                    leg = Legislator(term, 'upper', district, name,
                                     party=party, photo_url=photo_url,
                                     phone=phone, email=email)

                    leg.add_source(url)
                    self.save_legislator(leg)

    def scrape_house(self, term):
        url = 'http://www.camaraderepresentantes.org/cr_legs.asp'

        party_map = {'PNP': 'Partido Nuevo Progresista',
                     'PPD': u'Partido Popular Democr\xc3\xa1tico'}

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

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
                        district = 'At-Large'
                        first_name = last_name = ''

                    party = party_map[td.xpath('.//font')[1].text_content()]

                    leg = Legislator(term, 'lower', district, name,
                                     first_name=first_name,
                                     last_name=last_name,
                                     party=party,
                                     photo_url=photo_url)
                    leg.add_source(url)
                    self.save_legislator(leg)
