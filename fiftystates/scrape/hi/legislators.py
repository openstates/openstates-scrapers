from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import contextlib, itertools

class HILegislatorScraper(LegislatorScraper):
    state = 'hi'
    
    # From the itertools docs's recipe section 
    def grouper(self, n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return itertools.izip_longest(fillvalue=fillvalue, *args) 
    
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
            print "FAIL"
            #self.show_error(url, body)
            raise


    def scrape(self, chamber, year):
        # All other years are stored in a pdf
        # http://www.capitol.hawaii.gov/session2009/misc/statehood.pdf
        if int(year) != 2009:
            return
        
        if chamber == 'upper':
            legislators_page_url = "http://www.capitol.hawaii.gov/site1/info/direct/sendir.asp"
        else: 
            legislators_page_url = "http://www.capitol.hawaii.gov/site1/info/direct/repdir.asp"
            
        with self.lxml_context(legislators_page_url) as legislators_page: 
            legislators_table = legislators_page.cssselect('table')
            # Get the first table
            legislators_table = legislators_table[0]
            legislators_data = legislators_table.cssselect('tr')
            # Eliminate non-legislator element
            legislators_data.pop(0)
            
            # Group legislator data
            legislators_data = self.grouper(3, legislators_data)
            
            for name_and_party, district, email in legislators_data:
                for element, attribute, link, pos in name_and_party.iterlinks():
                    source = "http://www.capitol.hawaii.gov" + link      
                
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

                leg = Legislator(year, chamber, district, "",
                                 "", "", "", party,
                                 official_email=email)
                leg.add_source(source)
                self.save_legislator(leg)
