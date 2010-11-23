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
        
        with self.urlopen(bills_index_url) as page:
            page = lxml.html.fromstring(page)
            for bills_range in page.xpath(".//td[@width='16.6%']/a[last()]"):
                bills_range = bills_range.text_content()
                name = re.search("^([A-Z]+)", bills_range).groups()[0]
                
                if chamber == 'upper' and name.startswith('S'):
                    last = re.search("(\d+)$", bills_range).groups()[0]
                    bills_ranges[name] = { 'start': 0001, 'end': int(last) }
                elif chamber == 'lower' and name.startswith('H'):
                    last = re.search("(\d+)$", bills_range).groups()[0]
                    bills_ranges[name] = { 'start': 0001, 'end': int(last) }

        print bills_ranges
