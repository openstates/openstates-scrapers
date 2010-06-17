from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill

import lxml.html
import re, contextlib
import datetime as dt



class HIBillScraper(BillScraper):
    state = 'hi'
    
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
        session = "%s-%d" % (year, int(year) + 1)

        if int(year) >= 2009:
            self.scrape_session_2009(chamber, session)
        else:
            self.scrape_session_old(chamber, session)

    def scrape_session_2009(self, chamber, session):
        if chamber == "upper":
            url = "http://www.capitol.hawaii.gov/session2009/lists/RptIntroSB.aspx"
            type = "HB"
        else:
            url = "http://www.capitol.hawaii.gov/session2009/lists/RptIntroSB.aspx"
            type = "SB"
            
        with self.lxml_context(url) as page:
            for element, attribute, link, pos in page.iterlinks():         
                if re.search("billtype=" + type + "&billnumber=[0-9]+", link) != None:
                    bill_page_url = "http://www.capitol.hawaii.gov/session2009/lists/" + link
                    with self.lxml_context(bill_page_url) as bill_page:
                        bill_id = bill_page.get_element_by_id("LinkButtonMeasure")
                        print bill_id.text_content()
                        #bill = Bill(session, chamber, )
            

    def scrape_session_old(self, chamber, session):
        pass