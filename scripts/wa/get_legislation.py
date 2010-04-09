#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, string, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lxml.html
import contextlib
from pyutils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)
                                 

class WALegislationScraper(LegislationScraper):
  
  state = 'wa'

  @contextlib.contextmanager
  def lxml_context(self, url):
      body = self.urlopen(url)
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
	
	return full_name, first_name, middle_name, last_name

  def scrape_year(self, year):
      with self.lxml_context("http://apps.leg.wa.gov/billinfo/dailystatus.aspx?year=" + str(year)) as page:
	for element, attribute, link, pos in page.iterlinks():
		if re.search("bill=[0-9]{4}", link) != None:
			bill_page_url = "http://apps.leg.wa.gov/billinfo/" + link
			with self.lxml_context(bill_page_url) as bill_page:
				raw_title = bill_page.cssselect('title')
				split_title = string.split(raw_title[0].text_content(), ' ')
				bill_id = split_title[0] + ' ' + split_title[1]
				bill_id = bill_id.strip()
				session = split_title[3].strip()

				if (split_title[0] == 'SB'):
					chamber = 'upper'
				else: 
					chamber = 'lower'
				
				title_element = bill_page.get_element_by_id("ctl00_ContentPlaceHolder1_lblSubTitle")
				title = title_element.text_content()

				bill = 	Bill(session, chamber, bill_id, title)
				bill.add_source(bill_page_url)
				
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
							
				print 			
				print bill		
				self.add_bill(bill)

  
  def scrape_senators(self):
      with self.lxml_context("http://www.leg.wa.gov/Senate/Senators/Pages/default.aspx") as page:
	  senator_table = page.get_element_by_id("ctl00_PlaceHolderMain_dlMembers")
          senators = senator_table.cssselect('a')
	  for senator in senators:
		name = senator.text_content()
                separated_name = string.split(name, ' ')
		senator_page_url = "http://www.leg.wa.gov/senate/senators/Pages/" + separated_name[-1].lower() + ".aspx"
		with self.lxml_context(senator_page_url) as senator_page:
			try:
				full_name, first_name, middle_name, last_name = self.scrape_legislator_name(senator_page)
			except:
				break		 
	
			party_element = senator_page.get_element_by_id("ctl00_PlaceHolderMain_lblParty")
                        if party_element.text_content() == '(R)':
				party = 'Republican'
			else:
				party = 'Democrat'
  
			district_element = senator_page.get_element_by_id("ctl00_PlaceHolderMain_hlDistrict")
                        district = district_element.text_content()        
               
			legislator = Legislator('2009-2010', 'upper', district, full_name, first_name, last_name, middle_name, party)
			legislator.add_source(senator_page_url)
			self.add_legislator(legislator)

    
  def scrape_bills(self, chamber, year):
     if (year < 2009):
     	raise NoDataForYear(year)

     #self.scrape_senators()
     self.scrape_year(2009)
            
            
if __name__ == '__main__':
    WALegislationScraper.run()
    
