from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.co.utils import *

import lxml.html
import re, contextlib

class COLegislatorScraper(LegislatorScraper):
    state = 'co'
    
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
        # Legislator data only available for the current session
        year = year_from_session(session)

        if year != 2009:
            raise NoDataForPeriod(session)
        
        url = legs_url(chamber)
            
        with self.lxml_context(url) as page:
            # Iterate through legislator names
            for element, attribute, link, pos in page.iterlinks():
                with self.lxml_context(link) as legislator_page:
                    leg_elements = legislator_page.cssselect('b')
                    leg_name = leg_elements[0].text_content()
                 
                    district = ""
                    district_match = re.search("District [0-9]+", legislator_page.text_content())
                    if (district_match != None):
                        district = district_match.group(0)
                    
                    email = ""
                    email_match = re.search('E-mail: (.*)', legislator_page.text_content())
                    if (email_match != None):
                        email = email_match.group(1)
                        
                    form_page = lxml.html.parse(leg_form_url()).getroot()
                    form_page.forms[0].fields['Query'] = leg_name
                    result = lxml.html.parse(lxml.html.submit_form(form_page.forms[0])).getroot()
                    elements = result.cssselect('td')
                    party_letter = elements[7].text_content()
                    
                    party = party_name(party_letter)
                    
                    leg = Legislator(session, chamber, district, leg_name,
                                 "", "", "", party,
                                 official_email=email)
                    leg.add_source(link)
                    
                    self.save_legislator(leg)
