from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote

import datetime
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
        bill_types = {}
        
        with self.urlopen(bills_index_url) as page:
            page = lxml.html.fromstring(page)
            for bills_range in page.xpath(".//td[@width='16.6%']/a[last()]"):
                bills_range = bills_range.text_content()
                name = re.search("^([A-Z]+)", bills_range).groups()[0]
                
                if chamber == 'upper' and name.startswith('S'):
                    last = re.search("(\d+)$", bills_range).groups()[0]
                    bill_types[name] = { 'start': 0001, 'end': int(last) }
                elif chamber == 'lower' and name.startswith('H'):
                    last = re.search("(\d+)$", bills_range).groups()[0]
                    bill_types[name] = { 'start': 0001, 'end': int(last) }

        for bt in bill_types.keys():
            bill_num_range = range(bill_types[bt]['start'], bill_types[bt]['end']+1)
            bill_nums = [("%s%0*d" % (bt, 4, bn)) for bn in bill_num_range]
        
        
        for bn in bill_nums:
            bill_url = self.urls['info'] % (bn, ga_num)
            
            with self.urlopen(bill_url) as page:
                page = lxml.html.fromstring(page)
                title = page.xpath("//span[@id='lblAbstract']")[0].text
                
                bill = Bill(session, chamber, bn, title)
                bill.add_source(bill_url)
                
                # Primary Sponsor
                sponsor = page.xpath("//span[@id='lblBillSponsor']")[0].text_content().split("by")[-1]
                sponsor = sponsor.replace('*','').strip()
                bill.add_sponsor('primary',sponsor)
                
                # Co-sponsors unavailable for scraping (loaded in via AJAX)
                
                # Actions
                tables = page.xpath("//table[@class='bill-history-table']//table")
                if len(tables) > 1:
                    actions_table = tables[0] if chamber == 'lower' else tables[1]
                else:
                    actions_table = tables[0]
                action_rows = actions_table.xpath("tr[position()>1]")
                for ar in action_rows:
                    action_taken = ar.xpath("td")[0].text
                    action_date = datetime.datetime.strptime(ar.xpath("td")[1].text.strip(), '%m/%d/%Y')
                    bill.add_action(chamber, action_taken, action_date)
                
                
                self.save_bill(bill)
