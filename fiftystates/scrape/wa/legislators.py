from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import contextlib
import re, string

class WALegislatorScraper(LegislatorScraper):
    state = 'wa'
    
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
            self.show_error(url, body)
            raise
        
    def separate_name(self, full_name):
        separated_full_name = string.split(full_name, ' ')

        if len(separated_full_name) < 2:
            raise
        elif len(separated_full_name) == 2:
            first_name = separated_full_name[0]
            last_name = separated_full_name[1]
            middle_name = ''
        elif len(separated_full_name) == 3:
            first_name = separated_full_name[0]
            last_name = separated_full_name[2]
            middle_name = separated_full_name[1]
        else:
            first_name = separated_full_name[0]
            middle_name = separated_full_name[1]
            last_name_list = separated_full_name[1:]
            last_name = ""
            for name in last_name_list:
                last_name += name
      
        return full_name, first_name, middle_name, last_name 
        
    def scrape_legislator_name(self, senator_page):
        name_element = senator_page.get_element_by_id("ctl00_PlaceHolderMain_lblMemberName")
        name_text = name_element.text_content()
        full_name = name_text.replace('Senator', ' ')
        full_name = full_name.replace('Rep.', ' ')
        full_name = full_name.strip()

        return self.separate_name(full_name)
        
    def scrape_legislator_data(self, url, chamber):
        with self.lxml_context(url) as page:
            legislator_table = page.get_element_by_id("ctl00_PlaceHolderMain_dlMembers")
            legislators = legislator_table.cssselect('a')
            for legislator in legislators:
                name = legislator.text_content()
                full_name, first_name, middle_name, last_name = self.separate_name(name)
                name_for_url = last_name.lower()
                name_for_url = re.sub("'", "", name_for_url)
        
                if chamber == 'upper':
                    legislator_page_url = "http://www.leg.wa.gov/senate/senators/Pages/" + name_for_url + ".aspx"
                else: 
                    legislator_page_url = "http://www.leg.wa.gov/house/representatives/Pages/" + name_for_url + ".aspx"

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
                    self.add_legislator(legislator)
        
        def scrape_legislators(self, chamber, year):
            if year != '2009':
                raise NoDataForYear(year)

            if chamber == 'upper':
                self.scrape_legislator_data("http://www.leg.wa.gov/Senate/Senators/Pages/default.aspx", 'upper')

            else:
                self.scrape_legislator_data("http://www.leg.wa.gov/house/representatives/Pages/default.aspx", 'lower')
                     

