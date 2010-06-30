from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill

import lxml.html
import re, contextlib
import datetime as dt

class COBillScraper(BillScraper):
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
            raise

    def scrape(self, chamber, year):
        # Data prior to 1997 is contained in pdfs
        if year < '1997':
            raise NoDataForYear(year)
        
        bills_url = "http://www.leg.state.co.us/CLICS/CLICS" + year + "A/csl.nsf/%28bf-1%29?OpenView&Count=2000"
        with self.lxml_context(bills_url) as bills_page:
            table_rows = bills_page.cssselect('tr')
            for row in table_rows:
                print "row"
                row_elements = row.cssselect('td')
                
                bill_document = row_elements[0]
                bill_document.make_links_absolute("http://www.leg.state.co.us")
                links = []
                for element, attribute, link, pos in bill_document.iterlinks():
                    links.append(link)
                if len(links) > 1:
                    bill_document_link = links[0]
                    print bill_document_link
                
                    title_and_sponsors = row_elements[1]
                    title_and_sponsors_elements = title_and_sponsors.cssselect('font')
                    title = title_and_sponsors_elements[0].text_content()
                    print title
                    
#                for re in row_elements:
#                    print "row element"
#                    print re.text_content()
               