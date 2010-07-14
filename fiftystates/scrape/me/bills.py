import datetime

from fiftystates.scrape.me import metadata
from fiftystates.scrape.me.utils import chamber_name
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree

class MEBillScraper(BillScraper):
    state = 'me'

    def scrape(self, chamber, session):

        session = int(session)
        if session < 121:
            raise NoDataForPeriod(session)
        #For post data
        session_page_num = (session - 124) + 7
        
        self.scrape_bill(session, session_page_num)

    def scrape_bill(self, session, session_page_num):
        search_url = 'http://www.mainelegislature.org/LawMakerWeb/advancedsearch.asp'
        test_url = 'http://www.mainelegislature.org/LawMakerWeb/searchresults.asp?StartWith=1' 
        #post_data = 'PaperType=None&PaperNumberFrom=&PaperNumberTo=&LDNumberFrom=&LDNumberTo=&LegSession=8&LRType=None&LRNumberFrom=&LRNumberTo=&Title=&Subject=&Sponsor=None&Introducer=None&Committee=None&AmdFilingChamber=None&AmdFromFilingNumber=&AmdToFilingNumber=&RollcallChamber=None&RollcallNumber=&RollcallFromDate=&RollcallToDate=&Action=None&ActionChamber=None&ActionFromDate=&ActionToDate=&GovernorAction=None&Chapter=&FinalLawType=None&ClearFormVal=No&search.x=84&search.y=14&search=search' #% (session_page_num)
        post_data = 'PaperType=None&PaperNumberFrom=&PaperNumberTo=&LDNumberFrom=&LDNumberTo=&LegSession=8&LRType=None&LRNumberFrom=&LRNumberTo=&Title=&Subject=&Sponsor=None&Introducer=None&Committee=None&AmdFilingChamber=None&AmdFromFilingNumber=&AmdToFilingNumber=&RollcallChamber=None&RollcallNumber=&RollcallFromDate=&RollcallToDate=&Action=None&ActionChamber=None&ActionFromDate=&ActionToDate=&GovernorAction=None&Chapter=&FinalLawType=None&ClearFormVal=No&search.x=38&search.y=16&search=search'

        #with self.urlopen(search_url) as bill_seach_page:
        with self.urlopen(test_url, 'POST', post_data) as bill_list_page:
            root = lxml.etree.fromstring(bill_list_page, lxml.etree.HTMLParser())
            print root.xpath('string()')
