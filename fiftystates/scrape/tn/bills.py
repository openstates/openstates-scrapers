from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote

import lxml.html
import re


class TNBillScraper(BillScraper):
    state = 'tn'
    urls = {
        'index': 'http://wapp.capitol.tn.gov/apps/archives/default.aspx?year=%s',
        'info': 'http://wapp.capitol.tn.gov/apps/Billinfo/default.aspx?BillNumber=%s&ga=%s'
    }
    
    def scrape(self, chamber, session):
        ga_num = re.search("^(\d+)", session).groups()[0]
        bills_index_url = self.urls['index'] % (ga_num,)
        bills_ranges = {}
        
        with self.urlopen(bills_index_url) as bills_index_page:
            bills_index_page = lxml.html.fromstring(bills_index_page)
            lists = bills_index_page.xpath(".//td[@width='16.6%']")
            
            if chamber == "upper":
                bill_lists = {
                    'HB': lists[1],
                    'HJR': lists[3],
                    'HR': lists[5]
                }
            else:
                bill_lists = {
                    'SB': lists[0],
                    'SJR': lists[2],
                    'SR': lists[4]
                }
            
            for name, data in bill_lists.items():
                last_range = data.xpath("a")[-1].text_content()
                last_num = re.search("(\d+)$", last_range.split("-")[1]).groups()[0]
                bills_ranges[name] = { 'start': 0001, 'end': int(last_num) }

        print bills_ranges
                
            
