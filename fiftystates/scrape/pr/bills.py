from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.pr.utils import grouper, doc_link_url, year_from_session

import lxml.html
import contextlib
import datetime as dt

class PRBillScraper(BillScraper):
    state = 'pr'
    
    @contextlib.contextmanager
    def lxml_context(self, url):
        try:
            body = self.urlopen(url)
            elem = lxml.html.fromstring(body)
            yield elem
            
        except:
            self.warning('Couldnt open url: ' + url)
               
    def scrape(self, chamber, session):    
        bill_search_url = 'http://www.camaraderepresentantes.org/cr_buscar.asp'
        bill_types = {'Project':'P', 'Resolution':'R', \
                             'Joint Resolution':'RC', \
                             'Concurrent Resolution':'RK', \
                             'Appointment':'N'}
        #bodies = {'upper':'S', 'lower':'C'}
        bodies = {'upper':'S'}
        
        bill_search_page = lxml.html.parse(bill_search_url).getroot()
        search_form = bill_search_page.forms[0]
        
        for body in bodies.itervalues(): 
            for bill_type in bill_types.itervalues():   
                search_form.fields['cuerpo'] = body
                search_form.fields['tipo'] = bill_type
                search_form.fields['autor'] = 'NA'
                
                if year_from_session(session) == '2009':
                    search_form.fields['f2'] = '12/31/2009'
                elif year_from_session(session) == '2010':
                    search_form.fields['f1'] = '01/01/2010'
                
                result = lxml.html.parse(lxml.html.submit_form(search_form)).getroot()
                table_elements = result.cssselect('table')
                table_elements.pop()
                bill_elements = grouper(3, table_elements)
                
                for actions, complete_data, bill_data in bill_elements:
                    td_elements = bill_data.cssselect('td')  
                    title = td_elements[1].text_content()
                    date = td_elements[3].text_content()
                    description = td_elements[5].text_content()
                    authors = td_elements[7].text_content().split('/')
                    
                    bill = Bill(session, chamber, title, description)
                    
                    for author in authors:
                        if len(authors) == 1:
                            bill.add_sponsor('primary', author)
                        else:
                            bill.add_sponsor('cosponsor', author)
         
                    td_elements = actions.cssselect('td')
                    td_elements = td_elements[4:-1]                   
                    action_elements = grouper(3, td_elements)
                    
                    for date_element, action, empty in action_elements:
                        # Clean unicode character
                        date_text = date_element.text_content().replace(u'\xa0',u'')
                        date = dt.datetime.strptime(date_text, '%m/%d/%Y')
                        action_text = action.text_content()
                        try:
                            doc_link_part = action.iterlinks().next()[2]
                            if 'voto' in doc_link_part:
                                raise                           
                            doc_link = doc_link_url(doc_link_part)
                            bill.add_version((action_text, doc_link))
                        except:
                            pass
                    
                        bill.add_action(chamber, action_text, date)
                    
                           
                        
                    
                