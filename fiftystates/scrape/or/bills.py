from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill

import lxml.html
import re, contextlib, itertools, urllib
import datetime as dt

class ORBillScraper(BillScraper):
    state = 'or'
       
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
            raise
                    
    def scrape(self, chamber, year):
        
        bills_link = 'http://www.leg.state.or.us/bills_laws/billsinfo.htm'
        bills_sessions_pages = []
        
        with self.lxml_context(bills_link) as bills_page:
            for element, attribute, link, pos in bills_page.iterlinks():
                match = re.search("..(/measures[0-9]{2}s?.html)", link)
                if match != None:
                    bills_sessions_pages.append("http://www.leg.state.or.us" + match.group(1))
        
        shortened_year = int(year) % 100
        
        if shortened_year == 00:
            return
        
        pages_for_year = []
        
        for bsp in bills_sessions_pages:
            if str(shortened_year) in bsp:
                pages_for_year.append(bsp)
     
        measure_pages = []
     
        for pfy in pages_for_year:
            with self.lxml_context(pfy) as year_bills_page:
                for element, attribute, link, pos in year_bills_page.iterlinks():
                    if chamber == 'upper':
                        link_part = 'senmh'
                    else:
                        link_part = 'hsemh'
                    
                    regex = "[0-9]{2}(reg|ss[0-9])/pubs/" + link_part + ".(html|txt)"
                    match = re.search(regex, link)

                    if match != None:
                        measure_pages.append("http://www.leg.state.or.us/" + match.group(0))
        
        for mp in measure_pages:
            with self.lxml_context(mp) as measure_page:
                measures = measure_page.text_content()
        
                    
                
                

                        
                           
                        
                    
                