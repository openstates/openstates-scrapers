from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.co.utils import grouper, bills_url, year_from_session, base_url

import lxml.html
import re
import datetime as dt

class COBillScraper(BillScraper):
    state = 'co'
        
    def scrape_votes(self, link, chamber, bill):
        with self.urlopen(link) as votes_page_html:
            votes_page = lxml.html.fromstring(votes_page_html)
            page_tables = votes_page.cssselect('table')
            votes_table = page_tables[0]
            votes_elements = votes_table.cssselect('td')
            # Eliminate table headings and unnecessary element
            votes_elements = votes_elements[3:len(votes_elements)]
            ve = grouper(5, votes_elements)
            for actor, date, name_and_text, name, text in ve: 
                if 'cow' in text.text_content() or 'COW' in text.text_content():
                    continue
                vote_date = dt.datetime.strptime(date.text_content(), '%m/%d/%Y')
                motion_and_votes = text.text_content().lstrip('FINAL VOTE - ')
                motion, sep, votes = motion_and_votes.partition('.')
                if 'passed' in votes:
                    passed = True
                else:
                    passed = False

                votes_match = re.search('([0-9]+)-([0-9]+)-?([0-9]+)?', votes)
                yes_count = votes_match.group(1)
                no_count = votes_match.group(2)
                other_count = votes_match.group(3)
                        
                if other_count == None:
                    other_count = 0

                vote = Vote(chamber, vote_date, motion, passed, \
                            yes_count, no_count, other_count)
                vote.add_source(link)
                bill.add_vote(vote)
       
    def scrape_versions(self, link, bill):
        with self.urlopen(link) as versions_page_html:
                versions_page = lxml.html.fromstring(versions_page_html)
                page_tables = versions_page.cssselect('table')
                versions_table = page_tables[1]
                rows = versions_table.cssselect('tr')
                               
                for row in rows:
                    row_elements = row.cssselect('td')
                    if (len(row_elements) > 1):
                        version_name = row_elements[0].text_content()
                        documents_links_element = row_elements[2]
                        documents_links_element.make_links_absolute(base_url())
                        for element, attribute, link, pos in documents_links_element.iterlinks():
                            bill.add_version(version_name, link)
    
    def scrape_actions(self, link, bill):
        with self.urlopen(link) as actions_page_html:
                actions_page = lxml.html.fromstring(actions_page_html) 
                page_elements = actions_page.cssselect('b')
                actions_element = page_elements[3]
                actions = actions_element.text_content().split('\n')

                for action in actions:
                    date_regex = '[0-9]{2}/[0-9]{2}/[0-9]{4}'
                    date_match = re.search(date_regex, action)
                    action_date = date_match.group(0)
                    action_date_obj = dt.datetime.strptime(action_date, '%m/%d/%Y')

                    actor = ''
                    if 'House' in action:
                        actor = 'lower'
                    elif 'Senate' in action:
                        actor = 'upper'
                    elif 'Governor Action' in action:
                        actor = 'Governor'
                         
                    bill.add_action(actor, action, action_date_obj)
                    
    def scrape(self, chamber, session):   
        year = year_from_session(session)
        url = bills_url(year)
        with self.urlopen(url) as bills_page_html:
            bills_page = lxml.html.fromstring(bills_page_html)
            table_rows = bills_page.cssselect('tr')
            # Eliminate empty rows
            table_rows = table_rows[0:len(table_rows):2]
            for row in table_rows:
                row_elements = row.cssselect('td')
                
                bill_document = row_elements[0]
                bill_document.make_links_absolute(base_url())
                
                element, attribute, link, pos = bill_document.iterlinks().next()
                bill_id = element.text_content().rstrip('.pdf')
                bill_document_link = link           
                
                title_and_sponsors = row_elements[1]
                title_match = re.search('([A-Z][a-z]+.+[a-z])[A-Z]', title_and_sponsors.text_content())
                sponsors_match = re.search('[a-z]([A-Z]+.+)', title_and_sponsors.text_content())
                title = title_match.group(1)
                sponsors =  sponsors_match.group(1)
                separated_sponsors = sponsors.split('--')
                
                bill = Bill(session, chamber, bill_id, title)
                bill.add_version('current', bill_document_link)
                
                if separated_sponsors[1] == '(NONE)':
                    bill.add_sponsor('primary', separated_sponsors[0])
                
                else:
                    bill.add_sponsor('cosponsor', separated_sponsors[0])
                    bill.add_sponsor('cosponsor', separated_sponsors[1])                
               
                
                versions_page_element = row_elements[2]
                versions_page_element.make_links_absolute(base_url())
                element, attribute, link, pos = versions_page_element.iterlinks().next()
                
                bill.add_source(link)
                
                self.scrape_versions(link, bill)
                      
                actions_page_element = row_elements[3]
                element, attribute, link, pos = actions_page_element.iterlinks().next()
                frame_link = base_url() + link.split('?Open&target=')[1]
                
                self.scrape_actions(frame_link, bill)
                
                votes_page_element = row_elements[7]
                element, attribute, link, pos = votes_page_element.iterlinks().next()
                frame_link = base_url() + link.split('?Open&target=')[1]
                self.scrape_votes(frame_link, chamber, bill)
                                
                        
                           
                        
                    
                