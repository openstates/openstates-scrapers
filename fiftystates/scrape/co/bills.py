from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill

import lxml.html
import re, contextlib
import datetime as dt

class COBillScraper(BillScraper):
    state = 'co'
    
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
            raise
        
    def scrape_versions(self, link, bill):
            with self.lxml_context(link) as versions_page:
                    page_tables = versions_page.cssselect('table')
                    versions_table = page_tables[1]
                    rows = versions_table.cssselect('tr')
                                   
                    for row in rows:
                        row_elements = row.cssselect('td')
                        if (len(row_elements) > 1):
                            version_name = row_elements[0].text_content()
                            documents_links_element = row_elements[2]
                            documents_links_element.make_links_absolute("http://www.leg.state.co.us")
                            for element, attribute, link, pos in documents_links_element.iterlinks():
                                bill.add_version(version_name, link)
    
    def scrape_actions(self, link, bill):
        with self.lxml_context(link) as actions_page:
                page_elements = actions_page.cssselect('b')
                actions_element = page_elements[3]
                actions = actions_element.text_content().split('\n')

                for action in actions:
                    date_regex = '[0-9]{2}/[0-9]{2}/[0-9]{4}'
                    date_match = re.search(date_regex, action)
                    action_date = date_match.group(0)
                    action_date_obj = dt.datetime.strptime(action_date, '%m/%d/%Y')

                    actor = ''
                    if 'House' in action:
                        actor = 'lower'
                    elif 'Senate' in action:
                        actor = 'upper'
                    elif 'Governor Action' in action:
                        actor = 'Governor'
                         
                    bill.add_action(actor, action, action_date_obj)
                    
    def scrape(self, chamber, year):
        # Data prior to 1997 is contained in pdfs
        if year < '1997':
            raise NoDataForYear(year)
        
        bills_url = "http://www.leg.state.co.us/CLICS/CLICS" + year + "A/csl.nsf/%28bf-1%29?OpenView&Count=2000"
        with self.lxml_context(bills_url) as bills_page:
            table_rows = bills_page.cssselect('tr')
            # Eliminate empty rows
            table_rows = table_rows[0:len(table_rows):2]
            for row in table_rows:
                print "row"
                row_elements = row.cssselect('td')
                
                bill_document = row_elements[0]
                bill_document.make_links_absolute("http://www.leg.state.co.us")
                
                element, attribute, link, pos = bill_document.iterlinks().next()
                bill_id = element.text_content().rstrip('.pdf')
                bill_document_link = link           
                
                title_and_sponsors = row_elements[1]
                title_match = re.search('([A-Z][a-z]+.+[a-z])[A-Z]', title_and_sponsors.text_content())
                sponsors_match = re.search('[a-z]([A-Z]+.+)', title_and_sponsors.text_content())
                title = title_match.group(1)
                sponsors =  sponsors_match.group(1)
                separated_sponsors = sponsors.split('--')
                
                bill = Bill(year, chamber, bill_id, title)
                
                if separated_sponsors[1] == '(NONE)':
                    bill.add_sponsor('primary', separated_sponsors[0])
                
                else:
                    bill.add_sponsor('cosponsor', separated_sponsors[0])
                    bill.add_sponsor('cosponsor', separated_sponsors[1])                
               
                
                versions_page_element = row_elements[2]
                versions_page_element.make_links_absolute("http://www.leg.state.co.us")
                element, attribute, link, pos = versions_page_element.iterlinks().next()
                
                bill.add_source(link)
                
                self.scrape_versions(link, bill)
                      
                actions_page_element = row_elements[3]
                element, attribute, link, pos = actions_page_element.iterlinks().next()
                frame_link = "http://www.leg.state.co.us" + link.split('?Open&target=')[1]
                
                self.scrape_actions(frame_link, bill)
            
                
                        
                                
                        
                           
                        
                    
                