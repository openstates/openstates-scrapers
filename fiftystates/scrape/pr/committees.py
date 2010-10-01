import lxml.html
import contextlib
from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.committees import CommitteeScraper, Committee
from fiftystates.scrape.pr.utils import committees_url, grouper,\
    clean_newline, clean_space, between_keywords


class PRCommitteeScraper(CommitteeScraper):
    state = 'pr'
    
    @contextlib.contextmanager
    def lxml_context(self, url):
        try:
            body = self.urlopen(url)
            elem = lxml.html.fromstring(body)
            yield elem
            
        except:
            self.warning('Couldnt open url: ' + url)
    
    def scrape(self, chamber, term):
        # Data available for this term only
        if term != '2010':
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
        
        link = committees_pages['permanent']
        with self.lxml_context(link) as perm_committees_pages:
            a_elements = perm_committees_pages.cssselect('a')
            committee_elements = a_elements[1:-7]
            self.scrape_house_committee_data(committee_elements, link)
        
        link = committees_pages['special']
        with self.lxml_context(link) as special_committees_pages:
            a_elements = special_committees_pages.cssselect('a')
            committee_elements = a_elements[1:10]
            self.scrape_house_committee_data(committee_elements, link)
        
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
            
    def scrape_house_committee_data(self, committee_elements, link):
        for ce in committee_elements:
            link_part =  ce.iterlinks().next()[2]
            link = 'http://www.camaraderepresentantes.org/' + link_part
            name = ce.text_content()
            
            with self.lxml_context(link) as committee_page:
                td_elements = committee_page.cssselect('td')
                committee_data = td_elements[7]
                committee_text = clean_newline(committee_data.text_content())
                
                address = committee_text.split('Tel:')[0]
                telephone = clean_space(between_keywords('Fax:', 'Tel:', committee_text))                    
                tty = clean_space(between_keywords('Presidente', 'TTY:', committee_text))                                  
                president = clean_space(between_keywords('Vice Presidente:', 'Presidente:', committee_text))                    
                vicepresident = clean_space(between_keywords('Secretario(a):', 'Vice Presidente:', committee_text))
                secretary = clean_space(between_keywords('Repr', 'Secretario(a):', committee_text))
                majority_members = between_keywords('Miembros Minoria:', 'Miembros Mayor', committee_data.text_content())
                majority_members = majority_members[4:].split('\n')
                minority_members = committee_data.text_content().split('Miembros Minoria:')[1]
                minority_members = minority_members.split('\n')
                
            