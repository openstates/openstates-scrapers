from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

from tn import metadata

import datetime
import lxml.html
import re


class TNBillScraper(BillScraper):
    state = 'tn'
    urls = {
        'cur_index': 'http://wapp.capitol.tn.gov/apps/indexes/BillIndex.aspx?StartNum=%(chamber_type)sB0001&EndNum=%(chamber_type)sB9999&Year=%(year)s',
        'arch_index': 'http://wapp.capitol.tn.gov/apps/archives/BillIndex.aspx?StartNum=%(chamber_type)sB0001&EndNum=%(chamber_type)sB9999&Year=%(year)s',
        'info': 'http://wapp.capitol.tn.gov/apps/Billinfo/default.aspx?BillNumber=%s&ga=%s',
        'special': {
            '106th Special Session': 'http://wapp.capitol.tn.gov/apps/indexes/SpSession1.aspx',
            '104th Special Session': 'http://www.capitol.tn.gov/legislation/Archives/104GA/bills/SpecSessIndex.htm',
            '101st, 1st Special Session': 'http://www.capitol.tn.gov/legislation/Archives/101GA/bills/SpecSessIndex.htm',
            '101st, 2nd Special Session': 'http://www.capitol.tn.gov/legislation/Archives/101GA/bills/SpecSessIndex2.htm',
            '99th Special Session': 'http://www.capitol.tn.gov/legislation/Archives/99GA/bills/SpecSessIndex.htm'
        }
    }
    
    def scrape(self, chamber, session):
        chamber_type = 'S' if chamber == 'upper' else 'H'
        ga_num = re.search("^(\d+)", session).groups()[0]
        bill_types = {}
        
        if 'Special' in session:
            bills_index_url = self.urls['special'][session]
        else:
            if session in metadata["terms"][-1]["sessions"]:
              bills_index_url = self.urls['cur_index'] % {"chamber_type": chamber_type, "year": ga_num}
            else:
              bills_index_url = self.urls['arch_index'] % {"chamber_type": chamber_type, "year": ga_num}
        
        # Scrape session bills index to get bill numbers for current chamber
        with self.urlopen(bills_index_url) as page:
            page = lxml.html.fromstring(page)
        # Scrape bills
            for bill_link in page.xpath(".//div[@id='open']//a"):
               bn_formatted = bill_link.text
               self.scrape_bill(chamber, session, bn_formatted, ga_num)
        
    
    def scrape_bill(self, chamber, session, bill_number, ga_num):
        bill_url = self.urls['info'] % (bill_number, ga_num)

        with self.urlopen(bill_url) as page:
            page = lxml.html.fromstring(page)
            title = page.xpath("//span[@id='lblAbstract']")[0].text
            
            bill = Bill(session, chamber, bill_number, title)
            bill.add_source(bill_url)
            
            # Primary Sponsor
            sponsor = page.xpath("//span[@id='lblBillSponsor']")[0].text_content().split("by")[-1]
            sponsor = sponsor.replace('*','').strip()
            bill.add_sponsor('primary',sponsor)
            
            # Co-sponsors unavailable for scraping (loaded into page via AJAX)
            
            # Full summary doc
            summary = page.xpath("//span[@id='lblBillSponsor']/a")[0]
            bill.add_document('Full summary', summary.get('href'))
            
            # Actions
            tables = page.xpath("//table[@id='tabHistoryAmendments_tabHistory_gvBillActionHistory']")
            actions_table = tables[0]
            action_rows = actions_table.xpath("tr[position()>1]")
            for ar in action_rows:
                action_taken = ar.xpath("td")[0].text
                action_date = datetime.datetime.strptime(ar.xpath("td")[1].text.strip(), '%m/%d/%Y')
                bill.add_action(chamber, action_taken, action_date)

            votes_link = page.xpath("//span[@id='lblBillVotes']/a")
            if(len(votes_link) > 0):
                votes_link = votes_link[0].get('href')
                bill = self.scrape_votes(bill, sponsor, 'http://wapp.capitol.tn.gov/apps/Billinfo/%s' % (votes_link,))

            self.save_bill(bill)


    def scrape_votes(self, bill, sponsor, link):
        with self.urlopen(link) as page:
            page = lxml.html.fromstring(page)
            raw_vote_data = page.xpath("//span[@id='lblVoteData']")[0].text_content()
            raw_vote_data = raw_vote_data.strip().split('%s by %s - ' % (bill['bill_id'], sponsor))[1:]
            for raw_vote in raw_vote_data:
                raw_vote = raw_vote.split(u'\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0')
                motion = raw_vote[0]

                vote_date = re.search('(\d+/\d+/\d+)', motion)
                if vote_date:
                    vote_date = datetime.datetime.strptime(vote_date.group(), '%m/%d/%Y') 

                passed = ('Passed' in motion) or ('Adopted' in raw_vote[1])
                vote_regex = re.compile('\d+$')
                aye_regex = re.compile('^.+voting aye were: (.+) -')
                no_regex = re.compile('^.+voting no were: (.+) -')
                yes_count = None
                no_count = None
                other_count = 0
                ayes = []
                nos = []
                
                for v in raw_vote[1:]:
                    if v.startswith('Ayes...') and vote_regex.search(v):
                        yes_count = int(vote_regex.search(v).group())
                    elif v.startswith('Noes...') and vote_regex.search(v):
                        no_count = int(vote_regex.search(v).group())
                    elif aye_regex.search(v):
                        ayes = aye_regex.search(v).groups()[0].split(', ')
                    elif no_regex.search(v):
                        nos = no_regex.search(v).groups()[0].split(', ')

                if yes_count and no_count:
                    passed = yes_count > no_count
                else:
                    yes_count = no_count = 0


                vote = Vote(bill['chamber'], vote_date, motion, passed, yes_count, no_count, other_count) 
                vote.add_source(link)
                for a in ayes:
                    vote.yes(a)
                for n in nos:
                    vote.no(n)
                bill.add_vote(vote)

        return bill
