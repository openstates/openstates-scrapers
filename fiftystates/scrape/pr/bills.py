from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.pr.utils import grouper

import lxml.html
import contextlib

class PRBillScraper(BillScraper):
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
                    
    def scrape(self, chamber, year):    
        bill_search_url = 'http://www.camaraderepresentantes.org/cr_buscar.asp'
        bill_types = {'Project':'P', 'Resolution':'R', \
                             'Joint Resolution':'RC', \
                             'Concurrent Resolution':'RK', \
                             'Appointment':'N'}
        bodies = {'upper':'S', 'lower':'C'}
        
        bill_search_page = lxml.html.parse(bill_search_url).getroot()
        search_form = bill_search_page.forms[0]
        search_form.fields['cuerpo'] = bodies['upper']
        search_form.fields['tipo'] = bill_types['Project']
        search_form.fields['autor'] = 'NA'
        result = lxml.html.parse(lxml.html.submit_form(search_form)).getroot()
        table_elements = result.cssselect('table')
        table_elements.pop()
        bill_elements = grouper(3, table_elements)
        
        for actions, complete_data, bill_data in bill_elements:
            td_elements = bill_data.cssselect('td')  
            title = td_elements[1].text_content()
            date = td_elements[3].text_content()
            description = td_elements[5].text_content()
            authors = td_elements[7].text_content()
 
            td_elements = actions.cssselect('td')
            td_elements = td_elements[4:-1]
            
            action_elements = grouper(3, td_elements)
            for date, action, empty in action_elements:
                date = date.text_content()
                action = action.text_content()
            
                           
                        
                    
                