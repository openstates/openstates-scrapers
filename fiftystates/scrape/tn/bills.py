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
            bills_index_url = self.urls['index'] % (ga_num,)
        
        # Scrape session bills index to get bill numbers for current chamber
        with self.urlopen(bills_index_url) as page:
            page = lxml.html.fromstring(page)
            for bills_range in page.xpath(".//td[@width='16.6%']/a[last()]"):
                bills_range = bills_range.text_content()
                name, first, last = re.search("^([A-Z]+)(\d+)-[A-Z]+(\d+)$", bills_range).groups()
                if name.startswith(chamber_type):
                    bill_types[name] = { 'start': int(first), 'end': int(last) }
        
        # Scrape bills
        for bt in bill_types.keys():
            bill_num_range = range(bill_types[bt]['start'], bill_types[bt]['end']+1)
            #bill_nums += [("%s%0*d" % (bt, 4, bn)) for bn in bill_num_range]
            for bn in bill_num_range:
                bn_formatted = "%s%0*d" % (bt, 4, bn)
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

            print bill
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

                #print "Motion: %s" % (motion,)
                #print "Date: %s" % (vote_date,)
                #print "Passed: %s" % (passed,)
                #print "Yes: %s" % (yes_count,)
                #print "No: %s" % (no_count,)
                #print '------------'

                vote = Vote(bill['chamber'], vote_date, motion, passed, yes_count, no_count, other_count) 
                vote.add_source(link)
                for a in ayes:
                    vote.yes(a)
                for n in nos:
                    vote.no(n)
                bill.add_vote(vote)

        return bill
