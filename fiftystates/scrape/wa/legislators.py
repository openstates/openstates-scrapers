from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.wa.utils import separate_name, legs_url, year_from_session

import lxml.html
import re, contextlib

class WALegislatorScraper(LegislatorScraper):
    state = 'wa'
    
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
            raise
          
    def scrape(self, chamber, session):
        if year_from_session(session) != 2009:
            raise NoDataForPeriod(session)
        
        if chamber == 'upper':
            self.scrape_legislator_data("http://www.leg.wa.gov/Senate/Senators/Pages/default.aspx", 'upper')
        else:
            self.scrape_legislator_data("http://www.leg.wa.gov/house/representatives/Pages/default.aspx", 'lower')
                       
    def scrape_legislator_name(self, senator_page):
        name_element = senator_page.get_element_by_id("ctl00_PlaceHolderMain_lblMemberName")
        name_text = name_element.text_content()
        full_name = name_text.replace('Senator', ' ')
        full_name = full_name.replace('Rep.', ' ')
        full_name = full_name.strip()

        return separate_name(full_name)
        
    def scrape_legislator_data(self, url, chamber):
        with self.lxml_context(url) as page:
            legislator_table = page.get_element_by_id("ctl00_PlaceHolderMain_dlMembers")
            legislators = legislator_table.cssselect('a')
            for legislator in legislators:
                name = legislator.text_content()
                full_name, first_name, middle_name, last_name = separate_name(name)
                name_for_url = last_name.lower()
                name_for_url = re.sub("'", "", name_for_url)
        
                legislator_page_url = legs_url(chamber, name_for_url)

                with self.lxml_context(legislator_page_url) as legislator_page:
                    try:
                        full_name, first_name, middle_name, last_name = self.scrape_legislator_name(legislator_page)
                    except:
                        break     
    
                    party_element = legislator_page.get_element_by_id("ctl00_PlaceHolderMain_lblParty")
                    
                    if party_element.text_content() == '(R)':
                        party = 'Republican'
                    else:
                        party = 'Democrat'
  
                    district_element = legislator_page.get_element_by_id("ctl00_PlaceHolderMain_hlDistrict")
                    district = district_element.text_content()        
               
                    legislator = Legislator('2009-2010', chamber, district, full_name, "", "", "", party)
                    legislator.add_source(legislator_page_url)
                    self.save_legislator(legislator)
        
        

