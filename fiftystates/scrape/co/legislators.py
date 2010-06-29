from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import contextlib
import re

class COLegislatorScraper(LegislatorScraper):
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
            print "FAIL"
            #self.show_error(url, body)
            raise


    def scrape(self, chamber, year):
        if chamber == "upper":
            url = "http://www.leg.state.co.us/Clics/CLICS2010A/directory.nsf/MIWeb?OpenForm&chamber=Senate"
            type = "HB"
        else:
            url = "http://www.leg.state.co.us/Clics/CLICS2010A/directory.nsf/MIWeb?OpenForm&chamber=House"
            type = "SB"
        with self.lxml_context(url) as page:
            for element, attribute, link, pos in page.iterlinks():
                with self.lxml_context(link) as legislator_page:
                    leg_elements = legislator_page.cssselect('b')
                    leg_name = leg_elements[0].text_content()
                    print leg_name
#                    district_text = leg_elements[1].text_content()
#                    district_split = district_text.split(", ")
#                    district = ""
#                    if (len(district_split) > 1):
#                        district = district_split[1]
#                        if (re.search("District [0-9]+", district) == None):
#                            district_text = leg_elements[2].text_content()
#                            district_split = district_text.split(", ")
#                            district = district_split[1]
#                    print district
#                    
                    
                    district_match = re.search("District [0-9]+", legislator_page.text_content())
                    if (district_match != None):
                        print district_match.group(0)
                    
                    email_match = re.search('E-mail: (.*)', legislator_page.text_content())
                    if (email_match != None):
                        print email_match.group(1)
                        
                    form_page_url = "http://www.leg.state.co.us/Clics/CLICS2010A/csl.nsf/DirectoryHou?openframeset"
                    with self.lxml_context(form_page_url) as form_page:
                        form = form_page.forms[0]
                        print lxml.html.tostring(form)
                    
#                    leg = Legislator(year, chamber, district, "",
#                                 "", "", "", party,
#                                 official_email=email)
#                    leg.add_source(source)
#                    self.save_legislator(leg)
