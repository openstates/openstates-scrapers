from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.hi.utils import year_from_session, legs_url, base_url, grouper

import lxml.html
import contextlib

class HILegislatorScraper(LegislatorScraper):
    state = 'hi'
    
    @contextlib.contextmanager
    def lxml_context(self, url):
        try:
            body = self.urlopen(url)
            elem = lxml.html.fromstring(body)
            yield elem
            
        except:
            self.warning('Couldnt open url: ' + url)

    def scrape(self, chamber, session):
        # All other years are stored in a pdf
        # http://www.capitol.hawaii.gov/session2009/misc/statehood.pdf  
        if year_from_session(session) != 2009:
            raise NoDataForPeriod(session)
        
        legislators_page_url = legs_url(chamber)
            
        with self.urlopen(legislators_page_url) as legislators_page_str: 
            legislators_page = lxml.html.fromstring(legislators_page_str)
            legislators_table = legislators_page.cssselect('table')
            # Get the first table
            legislators_table = legislators_table[0]
            legislators_data = legislators_table.cssselect('tr')
            # Eliminate non-legislator element
            legislators_data.pop(0)
            
            # Group legislator data
            legislators_data = grouper(3, legislators_data)
            
            for name_and_party, district, email in legislators_data:
                element, attribute, link, pos = name_and_party.iterlinks().next()
                source = base_url() + link      
                
                name_and_party = name_and_party.cssselect('td')
                name_and_party = name_and_party[0]
                name, sep, party =  name_and_party.text_content().partition("(")
                # remove space at the beginning
                name = name.lstrip()
                
                if party == 'R)':
                        party = 'Republican'
                else:
                        party = 'Democrat'
                
                district = district.cssselect('td')
                district = district[1]
                district = district.text_content()
                
                email = email.cssselect('a')
                email = email[0]
                email = email.text_content()
                # Remove white space
                email = email.lstrip()

                leg = Legislator(session, chamber, district, name,
                                 "", "", "", party,
                                 official_email=email)
                leg.add_source(source)
                self.save_legislator(leg)
