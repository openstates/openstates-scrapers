from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill

import lxml.html
import re, string, contextlib
import datetime as dt

class WABillScraper(BillScraper):
    state = 'wa'
    
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
    
    def clean_string(self, s):
        return re.sub('[^0-9]', '', s)

    def scrape_year(self, year, chamber):    
        
        sep = '<h1>House</h1>'
            
        if chamber == 'upper':
            after = False
            reg = '[5-9]'
        else:
            after = True
            reg = '[1-4]'
                
        with self.lxml_context("http://apps.leg.wa.gov/billinfo/dailystatus.aspx?year=" + str(year), sep, after) as page:
            for element, attribute, link, pos in page.iterlinks():
                if re.search("bill=" + reg + "[0-9]{3}", link) != None:
                    bill_page_url = "http://apps.leg.wa.gov/billinfo/" + link
                    with self.lxml_context(bill_page_url) as bill_page:
                        raw_title = bill_page.cssselect('title')
                        split_title = string.split(raw_title[0].text_content(), ' ')
                        bill_id = split_title[0] + ' ' + split_title[1]
                        bill_id = bill_id.strip()
                        session = split_title[3].strip()

                        title_element = bill_page.get_element_by_id("ctl00_ContentPlaceHolder1_lblSubTitle")
                        title = title_element.text_content()

                        bill = Bill(session, chamber, bill_id, title)
                        bill.add_source(bill_page_url)
                
                        self.scrape_actions(bill_page, bill)
                
                        for element, attribute, link, pos in bill_page.iterlinks():
                            if re.search("billdocs", link) != None:
                                if re.search("Amendments", link) != None:
                                    bill.add_document("Amendment: " + element.text_content(), link)    
                                elif re.search("Bills", link) != None:
                                    bill.add_version(element.text_content(), link) 
                                else:
                                    bill.add_document(element.text_content(), link)
                            elif re.search("senators|representatives", link) != None:
                                with self.lxml_context(link) as senator_page:
                                    try:
                                        name_tuple = self.scrape_legislator_name(senator_page)
                                        bill.add_sponsor('primary', name_tuple[0])
                                    except:
                                        pass
                            elif re.search("ShowRollCall", link) != None:
                                match = re.search("([0-9]+,[0-9]+)", link)
                                match = match.group(0)
                                match = match.split(',')
                                id1 = match[0]
                                id2 = match[1]
                                url = "http://flooractivityext.leg.wa.gov/rollcall.aspx?id=" + id1 + "&bienId=" +id2
                                with self.lxml_context(url) as vote_page:
                                    self.scrape_votes(vote_page, bill, url)
                                    
                        self.save_bill(bill)
                        
    def scrape_votes(self, vote_page, bill, url): 
        date_match = re.search("[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}", vote_page.text_content())
        date_match = date_match.group(0)
        
        vote_date = dt.datetime.strptime(date_match, '%m/%d/%Y')
        
        votes = {"Yeas":0, "Nays":0, "Absent":0, "Excused":0}
        
        for type, number in votes.items():
            match = re.search(type + ": [0-9]+", vote_page.text_content())
            match = match.group(0)
            match = match.split(" ")
            number = match[1]
            
        passed = votes["Yeas"] > votes["Nays"] 
        
        chamber_match = re.search("(Senate|House) vote", vote_page.text_content())
        chamber_match = chamber_match.group(0)
        chamber_match = chamber_match.split(" ")
        chamber_match = chamber_match[0]
        
        if chamber_match == "Senate":
            chamber = "upper"
            title = "Senator"
        else:
            chamber = "lower"
            title = "Representative"
            
            
        motion_match = vote_page.cssselect('td[align="center"]')
        motion_match = motion_match[2]
        motion = motion_match.text_content()
        
        vote = Vote(chamber, vote_date, motion, passed, votes["Yeas"], votes["Nays"], votes["Absent"] + votes["Excused"])
        vote.add_source(url)   
        
        vote_elements = vote_page.cssselect('span[class="RollCall"]')
        
        vote_types = []
        
        for ve in vote_elements:
            voters = ve.text_content().split(", ")
            
            if len(voters) == 1:
                voters = voters[0].split(" and ")
                
            before, itself, after = voters[0].partition(title)
            voters[0] = after.lstrip("s ")
            voters[-1] = voters[-1].lstrip("and ")
                
            vote_types.append(voters)              
            
        for v in vote_types[0]:
            vote.yes(v)
        
        for v in vote_types[1]:
            vote.no(v)
            
        for v in vote_types[2]:
            vote.other(v)
     
        for v in vote_types[3]:
            vote.other(v)
        
        bill.add_vote(vote)
                        
    def scrape_actions(self, bill_page, bill):
        b_elements = bill_page.cssselect('b')
                        
        for e in b_elements:
            if re.search("[0-9]{4}", e.text_content()) != None:
                split_string = e.text_content().split()
                start_year = split_string[0]
                break
                            
        current_year = int(start_year)
        month_letters_to_numbers = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 'Jul':7, \
                                    'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}
                        
        action_dates = bill_page.cssselect('td[style="padding-left:20px"][nowrap="nowrap"][valign="top"]')
        action_texts = bill_page.cssselect('td[width="100%"]')
                                     
        last_month = 1
        
        for date, action_text in zip(action_dates, action_texts):
            splitted_date = date.text_content().split(" ")
            # If it is not a date skip  
            try:
                month = month_letters_to_numbers[splitted_date[0]]
            except:
                continue
            
            day = self.clean_string(splitted_date[1])

            if(last_month > month):
                current_year = current_year + 1
            last_month = month                                            
            bill.add_action('upper', action_text.text_content(), dt.datetime.strptime(str(month) + '/' + day + '/' + str(current_year), '%m/%d/%Y'))
    
    
    def scrape(self, chamber, year):
        if (year < 2005):
            raise NoDataForYear(year)

        self.scrape_year(year, chamber)