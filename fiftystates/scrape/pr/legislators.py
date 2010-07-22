from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import re, contextlib, itertools

class PRLegislatorScraper(LegislatorScraper):
    state = 'pr'
    
    @contextlib.contextmanager
    def lxml_context(self, url, sep=None, sep_after=True):
        try:
            body = self.urlopen(url)
        except:
            body = self.urlopen("http://www.google.com")
        
        if sep != None: 
            if sep_after == True:
                before, itself, body = body.rpartition(sep)
            else:
                body, itself, after = body.rpartition(sep)    
        
        elem = lxml.html.fromstring(body)
        
        try:
            yield elem
        except:
            print "FAIL"
            #self.show_error(url, body)
            raise
        
    # From the itertools docs's recipe section 
    def grouper(self, n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return itertools.izip_longest(fillvalue=fillvalue, *args) 

    def scrape(self, chamber, year):
        # Legislator data only available for the 2009 session
        if year != '2009':
            raise NoDataForYear(year)
        
        if chamber == 'upper':
            legislator_pages_dir = ('http://www.senadopr.us/Pages/Senadores%20de%20Mayoria.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20de%20Minoria.aspx',
                                'http://www.senadopr.us/senadores/Pages/Senadores%20Acumulacion.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20I.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20II.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20III.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20IV.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20V.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20VI.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20VII.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20VIII.aspx')
        else:
            legislator_pages_dir = 'http://www.camaraderepresentantes.org/legsv.asp'
            
        if chamber == 'upper':    
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
                        party = data_elements[2].text_content()
                        phone_no = data_elements[3].text_content()
                        email = data_elements[4].text_content()
                        
                            
#                        grouped_elements = self.grouper(4, data_elements)
#                        for name, party, phone_no, email in grouped_elements:
#                            print name.text_content()
#                            print party.text_content()
#                            print phone_no.text_content()
#                            print email.text_content()
                    
                    
        else:
            with self.lxml_context(legislator_pages_dir) as leg_page:
                tables = leg_page.cssselect('table')
                leg_dist_table = tables[4]
                leg_acu_table = tables[5]
                legs_dist = leg_dist_table.cssselect('td')
                legs_acu = leg_acu_table.cssselect('td')
                
                for l in legs_dist:
                    print len(l.cssselect('font')[0].cssselect('br'))
                    party = l.cssselect('font')[1].text_content()
                    pic_link_part = l.cssselect('a')[0].iterlinks().next()[2]
                    
#                
#                for l in legs_acu:
#                    print l.text_content()
#                    
#                
#                
        
