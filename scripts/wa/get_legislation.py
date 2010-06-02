#!/usr/bin/env python

import sys, os, string, re
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lxml.html
import contextlib
from pyutils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)
                                 

class WALegislationScraper(LegislationScraper):
  
    state = 'wa'

    metadata = {
        'state_name': 'Washington',
        'legislature_name': 'Washington Legislature',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Representative',
        'upper_term': 4,
        'lower_term': 2,
        'sessions': [],
        'session_details': {
            }
        }
    
    def clean_string(self, s):
        return re.sub('[^0-9]', '', s)

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
            self.show_error(url, body)
            raise

    def scrape_legislator_name(self, senator_page):
        name_element = senator_page.get_element_by_id("ctl00_PlaceHolderMain_lblMemberName")
        name_text = name_element.text_content()
        full_name = name_text.replace('Senator', ' ')
        full_name = full_name.replace('Rep.', ' ')
        full_name = full_name.strip()

        return self.separate_name(full_name)
        
    def separate_name(self, full_name):
        separated_full_name = string.split(full_name, ' ')    

        if len(separated_full_name) < 2:
            raise
        elif len(separated_full_name) == 2:
            first_name = separated_full_name[0]
            last_name = separated_full_name[1]
            middle_name = ''
        elif len(separated_full_name) == 3:
            first_name = separated_full_name[0]
            last_name = separated_full_name[2]
            middle_name = separated_full_name[1]
        else:
            first_name = separated_full_name[0]
            middle_name = separated_full_name[1]
            last_name_list = separated_full_name[1:]
            last_name = ""
            for name in last_name_list:
                last_name += name
      
        return full_name, first_name, middle_name, last_name 
    
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
            print date.text_content()
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
            bill.add_action('upper', action_text.text_content(), datetime.strptime(str(month) + '/' + day + '/' + str(current_year), '%m/%d/%Y'))
                            
                                    

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
                                    
                        self.add_bill(bill)

  
    def scrape_legislator_data(self, url, chamber):
        with self.lxml_context(url) as page:
            legislator_table = page.get_element_by_id("ctl00_PlaceHolderMain_dlMembers")
            legislators = legislator_table.cssselect('a')
            for legislator in legislators:
                name = legislator.text_content()
                full_name, first_name, middle_name, last_name = self.separate_name(name)
                name_for_url = last_name.lower()
                name_for_url = re.sub("'", "", name_for_url)
        
                if chamber == 'upper':
                    legislator_page_url = "http://www.leg.wa.gov/senate/senators/Pages/" + name_for_url + ".aspx"
                else: 
                    legislator_page_url = "http://www.leg.wa.gov/house/representatives/Pages/" + name_for_url + ".aspx"

                with self.lxml_context(legislator_page_url) as legislator_page:
                    try:
                        full_name, first_name, middle_name, last_name = self.scrape_legislator_name(legislator_page)
                    except:
                        break     
    
                    party_element = legislator_page.get_element_by_id("ctl00_PlaceHolderMain_lblParty")
                    
                    if party_element.text_content() == '(R)':
                        party = 'Republican'
                    else:
                        party = 'Democrat'
  
                    district_element = legislator_page.get_element_by_id("ctl00_PlaceHolderMain_hlDistrict")
                    district = district_element.text_content()        
               
                    legislator = Legislator('2009-2010', chamber, district, full_name, first_name, last_name, middle_name, party)
                    legislator.add_source(legislator_page_url)
                    self.add_legislator(legislator)

    
    def scrape_bills(self, chamber, year):
        if (year < 2005):
            raise NoDataForYear(year)

        self.scrape_year(year, chamber)

    def scrape_legislators(self, chamber, year):
        if year != '2009':
            raise NoDataForYear(year)

        #if chamber == 'upper':
        #    self.scrape_legislator_data("http://www.leg.wa.gov/Senate/Senators/Pages/default.aspx", 'upper')

        #else:
        #    self.scrape_legislator_data("http://www.leg.wa.gov/house/representatives/Pages/default.aspx", 'lower')
                     
if __name__ == '__main__':
    WALegislationScraper.run()
    

