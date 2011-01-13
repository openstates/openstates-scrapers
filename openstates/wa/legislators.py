from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.wa.utils import year_from_session

import lxml.html
import re
import string

def separate_name(full_name):
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

def house_url(chamber):
    if chamber == "upper":
        return "http://www.leg.wa.gov/Senate/Senators/Pages/default.aspx"
    else:
        return "http://www.leg.wa.gov/house/representatives/Pages/default.aspx"

def legs_url(chamber, name_for_url):
    if chamber == 'upper':
        return "http://www.leg.wa.gov/senate/senators/Pages/" + name_for_url + ".aspx"
    else:
        return "http://www.leg.wa.gov/house/representatives/Pages/" + name_for_url + ".aspx"

class WALegislatorScraper(LegislatorScraper):
    state = 'wa'
          
    def scrape(self, chamber, session):
        if year_from_session(session) != 2009:
            raise NoDataForPeriod(session)
        
        if chamber == 'upper':
            self.scrape_legislator_data('upper', session)
        else:
            self.scrape_legislator_data('lower', session)
                       
    def scrape_legislator_name(self, senator_page):
        name_element = senator_page.get_element_by_id("ctl00_PlaceHolderMain_lblMemberName")
        name_text = name_element.text_content()
        full_name = name_text.replace('Senator', ' ')
        full_name = full_name.replace('Rep.', ' ')
        full_name = full_name.strip()

        return separate_name(full_name)
        
    def scrape_legislator_data(self, chamber, session):
        with self.urlopen(house_url(chamber)) as page_html:
            page = lxml.html.fromstring(page_html)
            legislator_table = page.get_element_by_id("ctl00_PlaceHolderMain_dlMembers")
            legislators = legislator_table.cssselect('a')
            for legislator in legislators:
                name = legislator.text_content()
                full_name, first_name, middle_name, last_name = separate_name(name)
                name_for_url = last_name.lower()
                name_for_url = re.sub("'", "", name_for_url)
        
                legislator_page_url = legs_url(chamber, name_for_url)

                with self.urlopen(legislator_page_url) as legislator_page_html:
                    legislator_page = lxml.html.fromstring(legislator_page_html)
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
               
                    legislator = Legislator(session, chamber, district, full_name, "", "", "", party)
                    legislator.add_source(legislator_page_url)
                    self.save_legislator(legislator)
        
        

