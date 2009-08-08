#!/usr/bin/env python

import datetime
import logging
import os
import re
import sys

import html5lib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import *

# Logging
logging.basicConfig(level=logging.DEBUG)

class NDLegislationScraper(LegislationScraper):
    """
    Scrapes available legislative information from the website of the North
    Dakota legislature and stores it in the fiftystates backend.
    """    
    state = 'nd'
    site_root = 'http://www.legis.nd.gov'
    parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup'))
    
    metadata = {
        'state_name': 'North Dakota',
        'legislature_name': 'North Dakota Legislative Assembly',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Representative',
        # Either member may also serve a four-year term,
        # See http://www.legis.nd.gov/assembly/ for details
        'upper_term': 2,
        'lower_term': 2,
        'sessions': ['1997', '1999', '2001', '2003', '2005', '2007', '2009'],
        'session_details': {
            '1997': {'years': [1997, 1998], 'sub_sessions': [], 
                     'alternate': '55th', 'number': 55},
            '1999': {'years': [1999, 2000], 'sub_sessions': [], 
                     'alternate': '56th', 'number': 56},
            '2001': {'years': [2001, 2002], 'sub_sessions': [], 
                     'alternate': '57th', 'number': 57},
            '2003': {'years': [2003, 2004], 'sub_sessions': [], 
                     'alternate': '58th', 'number': 58},
            '2005': {'years': [2005, 2006], 'sub_sessions': [], 
                     'alternate': '59th', 'number': 59},
            '2007': {'years': [2007, 2008], 'sub_sessions': [], 
                     'alternate': '60th', 'number': 60},
            '2009': {'years': [2009, 2010], 'sub_sessions': [], 
                     'alternate': '61th', 'number': 61},
            }
        }      
    
    def scrape_legislators(self, chamber, year):
        """
        Scrape the ND legislators seated in a given chamber during a given year.
        """
        # Error checking
        if year not in self.metadata['session_details']:
            raise NoDataForYear(year)
        
        # URL building
        if chamber == 'upper':
            url_chamber_name = 'senate'
            url_member_name = 'senators'
        else:
            url_chamber_name = 'house'
            url_member_name = 'representatives'
        
        assembly_url = '/assembly/%i-%s/%s' % (
            self.metadata['session_details'][str(year)]['number'],
            year,
            url_chamber_name)
        
        list_url = \
            self.site_root + \
            assembly_url + \
            '/members/last-name.html'    
        
        # Parsing
        soup = self.parser.parse(self.urlopen(list_url))
        
        if not soup:
            raise ScrapeError('Failed to parse legaslative list page.')
        
        header = soup.find('h2')
        
        if not header:
            raise ScrapeError('Legaslative list header element not found.')
        
        table = header.findNextSibling('table')
        
        member_links = table.findAll('a')
        
        for link in member_links:
            # Populate base attributes
            attributes = {
                'session': year,
                'chamber': chamber,
                }
            
            # Parse member page
            attributes.update(
                self.scrape_legislator_bio(self.site_root + link['href']))
        
            logging.debug(attributes)
        
            # Save
            legislator = Legislator(**attributes)
            self.add_legislator(legislator)
    
    def scrape_legislator_bio(self, url):
        """
        Scrape the biography page of a specific ND legislator.
        
        Note that some parsing is conditional as older bio pages are not
        formatted exactly as more recent ones are.
        """
        # Parsing
        soup = self.parser.parse(self.urlopen(url))
        
        attributes = {}
        
        # Name
        label = soup.find(re.compile('^(h1|h2)'))
        name_match = re.match('(Senator|Representative) (.*)', label.contents[0])
        attributes['full_name'] =  name_match.group(2).strip()
        parts = attributes['full_name'].split()
        
        if len(parts) > 2:
            attributes['first_name'] = parts[0].strip()
            attributes['middle_name'] = parts[1].strip(' .')
            attributes['last_name'] = parts[2].strip()
        else:
            attributes['first_name'] = parts[0].strip()
            attributes['middle_name'] = u''
            attributes['last_name'] = parts[1].strip()
        
        # Other required data
        label = soup.find(text=re.compile('Party:')).parent
        
        if label.name == 'span':     
            attributes['party'] = \
                label.parent.findNextSibling('td').contents[0]
        else:
            attributes['party'] = label.nextSibling
        
        label = soup.find(text=re.compile('District:')).parent
        
        if label.name == 'span':     
            attributes['district'] = \
                label.parent.findNextSibling('td').contents[0]
        else:
            attributes['district'] = label.nextSibling 
        
        # Supplemental data
        label = soup.find(text=re.compile('Address:'))
        attributes['address'] = \
            label.parent.parent.findNextSibling('td').contents[0]
            
        label = soup.find(text=re.compile('Telephone:'))
        attributes['telephone'] = \
            label.parent.parent.findNextSibling('td').contents[0]
        
        label = soup.find(text=re.compile('E-mail:'))
        email = label.parent.parent.findNextSibling('td').contents[0]
        
        if hasattr(email, 'contents'):
            attributes['email'] = email.contents[0]
        else:
            if email != 'None':
                attributes['email'] = email
            else:
                attributes['email'] = u''
            
        return attributes  

    def scrape_bills(self, chamber, year):
        """
        Scrape the ND bills considered in a given chamber during a given year.
        """
        # Error checking
        if year not in self.metadata['session_details']:
            raise NoDataForYear(year)
        
        # URL building
        if chamber == 'upper':
            url_chamber_name = 'senate'
            norm_chamber_name = 'Senate'
            bill_prefix = 'SB'
        else:
            url_chamber_name = 'house'
            norm_chamber_name = 'House'
            bill_prefix = 'HB'
        
        assembly_url = '/assembly/%i-%s' % (
            self.metadata['session_details'][str(year)]['number'],
            year)
        
        chamber_url = '/bill-text/%s-bill.html' % (url_chamber_name)
        
        list_url = self.site_root + assembly_url + chamber_url
        
        # Parsing
        soup = self.parser.parse(self.urlopen(list_url))
        
        if not soup:
            raise ScrapeError('Failed to parse legaslative list page.')
        
        table = soup.find('table', summary=norm_chamber_name + ' Bills')
        
        bill_links = table.findAll('a', href=re.compile('bill-actions'))
        indexed_bills = []
        
        for link in bill_links:
            # Populate base attributes
            attributes = {
                'session': year,
                'chamber': chamber,
                }
            
            bill_number = link.contents[0]
            
            if not re.match('^[0-9]{4}$', bill_number):
                raise ScrapeError('Bill number not in expected format.')
            
            attributes['bill_id'] = bill_prefix + ' ' + bill_number
            
            # Skip duplicates (bill is listed once for each version)
            if attributes['bill_id'] in indexed_bills:
                continue
            
            indexed_bills.append(attributes['bill_id'])
            
            # Parse details page                
            attributes.update(
                self.scrape_bill_details(assembly_url, bill_number))
        
            logging.debug(attributes)
        
            # Create bill
            bill = Bill(**attributes)
            
            # Parse actions            
            actions = self.scrape_bill_actions(assembly_url, bill_number, year)
            
            for action in actions:
                bill.add_action(**action)
                
            logging.debug('%i actions' % len(actions))

            # Parse versions
            versions = self.scrape_bill_versions(assembly_url, bill_number)
            
            for version in versions:
                bill.add_version(**version)
                
            logging.debug('%i versions' % len(versions))
                
            # Save bill
            self.add_bill(bill)
            
    def scrape_bill_details(self, assembly_url, bill_number):
        """
        Scrape details from the history page of a specific ND bill.
        """
        url = \
            self.site_root + \
            assembly_url + \
            ('/bill-actions/ba%s.html' % bill_number)
                
        # Parsing
        soup = self.parser.parse(self.urlopen(url))
        
        attributes = {}
        
        # Bill title
        table = soup.find('table', summary='Measure Number Breakdown')
        
        text = ''
        
        rows = table.findAll('tr')
        
        # Skip the first two rows relating too who introduced the bill
        i = 2
        
        while not rows[i].find('hr'):
            text = text + ' ' + rows[i].td.contents[0].strip()
            i = i + 1
            
        attributes['title'] = text
        
        return attributes
    
    def scrape_bill_actions(self, assembly_url, bill_number, year):
        """
        Scrape actions from the history page of a specific ND bill.
        """
        url = \
            self.site_root + \
            assembly_url + \
            ('/bill-actions/ba%s.html' % bill_number)
            
        # Parsing
        soup = self.parser.parse(self.urlopen(url))
        
        actions = []
        
        table = soup.find('table', summary='Measure Number Breakdown')
        
        headers = table.findAll('th')
        
        # These fields must be stored temporarily as they are not repeated on 
        # every row
        action_date = None
        actor = None
        
        for header in headers:
            action = {}
            
            # Both the date and actor fields may be empty to indicate that
            # they repeat from the previous row
            if len(header.contents) != 0 and \
                header.contents[0].strip() != '':
                action_date = datetime.datetime(
                    int(year),
                    int(header.contents[0][0:2]), 
                    int(header.contents[0][3:5]))
                
            action['date'] = action_date
            
            actor_cell = header.nextSibling.nextSibling.nextSibling.nextSibling
            
            if len(actor_cell.contents) != 0 and \
                actor_cell.contents[0].strip() != '':
                if actor_cell.contents[0] == 'Senate':
                    actor = u'upper'
                elif actor_cell.contents[0] == 'House':
                    actor = u'lower'
                
            action['actor'] = actor
                
            action_cell = actor_cell.nextSibling.nextSibling.nextSibling.nextSibling
            
            action['action'] = action_cell.contents[0].replace('\n', '')
            
            actions.append(action)
            
        return actions            
    
    def scrape_bill_versions(self, assembly_url, bill_number):
        """
        Scrape URLs from the versions page of a specific ND bill.
        """
        url = \
            self.site_root + \
            assembly_url + \
            '/bill-index/bi%s.html' % bill_number
        
        # Parsing
        soup = self.parser.parse(self.urlopen(url))
        
        versions = []
        
        table = soup.find('table', summary=re.compile('Measure Number Breakdown'))
        
        headers = table.findAll('th')
        
        for header in headers:
            version = {}
            
            doc_id = header.contents[0]
            
            version_element = header.nextSibling.nextSibling
            
            # Some years seem are parsed as though there are additional tags
            # separating these cells... bad markup / unterminated tags to blame?
            if version_element.contents[0] == '.':
                version_element = version_element.nextSibling.nextSibling
                
            pdf_url = version_element.contents[0]['href'].lstrip('.')
            version['url'] = \
                self.site_root + \
                assembly_url + \
                pdf_url                
            
            version_id = version_element.contents[0].contents[0]
            
            version['id'] = "%s.%s" % (doc_id, version_id)
            
            name_element = version_element.nextSibling.nextSibling
            
            # See above comment
            if name_element.contents[0].strip() == '':
                name_element = name_element.nextSibling.nextSibling
                
            version['name'] = name_element.contents[0].strip()
            
            versions.append(version)
            
        return versions        
    
if __name__ == '__main__':
    NDLegislationScraper().run()
