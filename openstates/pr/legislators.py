# coding=utf-8
from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from lxml import etree
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
                doc.make_links_absolute(url)
                table = doc.xpath('//table[@summary="Listado de Senadores"]')[0]

                # skip first row
                for row in table.xpath('tr')[1:]:
                    tds = row.xpath('td')
                    name = tds[0].text_content().title().replace('Hon.','',1).strip()
		    if name == "Luz Z.Arce Ferrer":
			name = "Luz Z. Arce Ferrer"
                    party = tds[1].text_content()
                    phone = tds[2].text_content()
                    email = tds[3].text_content()
                    #shapefiles denote 0 as At-Large Districts
                    if counter == 0:
                        district = 'At-Large'
                    else:
                        district = str(counter)
		    
                    leg = Legislator(term, 'upper', district, name,
                                     party=party, phone=phone, email=email)

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
                for td in table.xpath('.//td'):
                    photo_url = td.xpath('.//img/@src')[0]
		    rep_url = td.xpath('a/@href')[0]
		    #go into the legislator page and get his data
		    with self.urlopen(rep_url) as leg_html:
			leg_doc = lxml.html.fromstring(leg_html)
			leg_doc.make_links_absolute(rep_url)
			leg_tables = leg_doc.xpath('//table[@class="lcom"]')
			#if len(tables) == 1:
	    		#    email = tables[0]
			#else:
			#    email = tables[1]
		#	for ulu in leg_tables:
		#	    print lxml.etree.tostring(ulu).replace('&#13;','')
		#	    print '---------'
#			print leg_tables[1].xpath('//div[@class="sbox2"][2]/div[2]/table/tbody/tr[1]/td[2]')
#			print lxml.etree.tostring(leg_tables[1].xpath('//div[@class="sbox2"]/[1]'))
#			print lxml.etree.tostring(leg_tables[1]).find('td').replace('<br>','').replace('<br/>','')
			email =  leg_tables[1].xpath('//a[starts-with(@href,"mailto")]')[0].text
			return
			#print tables[1].find('font')
			#print tables[0].find('font')
			#print lxml.etree.tostring(email)
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
		    if name == u"Carlos  “Johnny” Méndez Nuñez":
			name = u"Carlos “Johnny” Méndez Nuñez"
                    leg = Legislator(term, 'lower', district, name,
                                     first_name=first_name,
                                     last_name=last_name,
                                     party=party,
                                     photo_url=photo_url,email=email)
                    leg.add_source(rep_url)
                    self.save_legislator(leg)
