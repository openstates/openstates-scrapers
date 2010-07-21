from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import re, contextlib, csv, urllib

class PRLegislatorScraper(LegislatorScraper):
    state = 'pr'
    
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
        # Legislator data only available for the 2009 session
        if year != '2009':
            raise NoDataForYear(year)
        
