import lxml.html
import contextlib
from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.committees import CommitteeScraper, Committee
from fiftystates.scrape.pr.utils import committees_url, grouper


class PRCommitteeScraper(CommitteeScraper):
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
    
    def scrape(self, chamber, term):
        # Data available for this term only
        if term != '2010-2011':
            raise NoDataForPeriod(term)  

        if chamber == "upper":
            self.scrape_senate()
        elif chamber == "lower":
            self.scrape_house()
    
    def scrape_senate(self):
        committees_pages = committees_url('upper')
        
        link = committees_pages['permanent']
        with self.lxml_context(link) as perm_committees_page:
            td_elements = perm_committees_page.cssselect('td')     
            self.scrape_senate_comittee_data(td_elements[129:201], link)
        
        link = committees_pages['special']
        with self.lxml_context(link) as special_committees_page:
            td_elements = special_committees_page.cssselect('td')         
            self.scrape_senate_comittee_data(td_elements[129:138], link)
        
        link = committees_pages['joint']
        with self.lxml_context(link) as joint_committees_page:
            td_elements = joint_committees_page.cssselect('td')
            self.scrape_senate_comittee_data(td_elements[129:156], link)  
            
    def scrape_house(self):
        committees_pages = committees_url('lower')
        
    def scrape_senate_comittee_data(self, committee_elements, link):
        committees_grouped = grouper(3, committee_elements)
            
        for commission, type, president in committees_grouped:
            link_part = commission.iterlinks().next()[2]
            com_link = 'http://senadopr.us' + link_part
            name = commission.text_content()
            com_president = president.text_content()

            com = Committee('upper', name, president = com_president)
            com.add_source(com_link)
            com.add_source(link)
            