from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.pr.utils import legislators_url, year_from_session

import lxml.html
import re, contextlib

class PRLegislatorScraper(LegislatorScraper):
    state = 'pr'
    
    @contextlib.contextmanager
    def lxml_context(self, url):
        try:
            body = self.urlopen(url)
        except:
            body = self.urlopen("http://www.google.com") 
        
        elem = lxml.html.fromstring(body)
        
        try:
            yield elem
        except:
            print "FAIL"
            #self.show_error(url, body)
            raise

    def scrape(self, chamber, session):
        # Data available for this session only
        if year_from_session(session) != 2010:
            raise NoDataForPeriod(session)
        
        if chamber == 'upper':
            self.scrape_senate(session)
        elif chamber == 'lower':
            self.scrape_house(session)
                    
    def scrape_senate(self, session):
        legislator_pages_dir = legislators_url('upper')
        
        for counter, leg_page_dir in enumerate(legislator_pages_dir):
            with self.lxml_context(leg_page_dir) as leg_page:
                tables = leg_page.cssselect('table')
                legislators_table = tables[62]
                leg_data = legislators_table.cssselect('tr')
                # remove table header
                leg_data = leg_data[5:]
                for ld in leg_data:
                    data_elements = ld.cssselect('td')
                   
                    pic_link_part = data_elements[0].iterlinks().next()[2]
                    pic_link = 'http://www.senadopr.us' + pic_link_part
                    name = data_elements[1].text_content()
                    link_part = data_elements[1].iterlinks().next()[2]
                    link = 'http://www.senadopr.us' + link_part
                    leg_party = data_elements[2].text_content()
                    leg_phone_no = data_elements[3].text_content()
                    leg_email = data_elements[4].text_content()
                   
                    if counter == 0:
                        dist = 'at-large'
                    else:
                        dist = counter                     
                   
                    leg = Legislator(session, 'upper', str(dist), name, \
                                     party = leg_party, head_shot = pic_link, \
                                     phone = leg_phone_no, email = leg_email)
                    leg.add_source(link)
                    leg.add_source(leg_page_dir)
                    self.save_legislator(leg)
    
    def scrape_house(self, session):
        legislator_pages_dir = legislators_url('lower')
        
        with self.lxml_context(legislator_pages_dir) as leg_page:
                tables = leg_page.cssselect("table")
                leg_dist_table = tables[4]
                leg_acu_table = tables[5]
                legs_dist = leg_dist_table.cssselect('td')
                legs_acu = leg_acu_table.cssselect('td')
                # last one is empty
                legs_acu.pop()
                
                for l in legs_dist:
                    leg_data = l.cssselect('font')
                    name_dist_party = leg_data[0].text_content()
                    name, sep, dist_party = name_dist_party.partition('Distrito')
                    dist = re.search('[0-9]+', dist_party).group(0)
                    leg_party = leg_data[1].text_content()
                    name = name.lstrip()
                    link_part = l.cssselect('a')[0].iterlinks().next()[2]
                    link = 'http://www.camaraderepresentantes.org/' + link_part
                    imgs = l.cssselect('img')
                    pic_link_part = imgs[0].iterlinks().next()[2]
                    pic_link = 'http://www.camaraderepresentantes.org/' + pic_link_part

                    leg = Legislator(session, 'lower', dist, name, \
                                     party = leg_party, head_shot = pic_link)
                    leg.add_source(link)
                    leg.add_source(legislator_pages_dir)
                    self.save_legislator(leg)
                 
                for l in legs_acu:
                    link_part = l.iterlinks().next()[2]
                    link = 'http://www.camaraderepresentantes.org/' + link_part
                    pic_link_part = l.cssselect('img')[0].iterlinks().next()[2]
                    pic_link = 'http://www.camaraderepresentantes.org/' + pic_link_part
                    name_party = l.text_content().lstrip()
                    match = re.search('PNP|PPD', name_party)
                    name = name_party[:-4]
                    leg_party = match.group(0) 
                                                                               
                    leg = Legislator(session, 'lower', 'at-large', name, \
                                     party = leg_party, head_shot = pic_link)
                    
                    leg.add_source(link)
                    leg.add_source(legislator_pages_dir)
                    self.save_legislator(leg)
        
               
              

