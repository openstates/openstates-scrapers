#!/usr/bin/env python

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
        # See http://www.legis.nd.gov/assembly/
        'upper_term': 2,
        'lower_term': 2,
        'sessions': ['1997', '1998', '1999', '2000', '2001', '2002', '2003',
                     '2004', '2005', '2006', '2007', '2008', '2009'],
        'session_details': {
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
                label.parent.findNextSibling('td').contents
        else:
            attributes['party'] = label.nextSibling
        
        label = soup.find(text=re.compile('District:')).parent
        
        if label.name == 'span':     
            attributes['district'] = \
                label.parent.findNextSibling('td').contents
        else:
            attributes['district'] = label.nextSibling 
        
        # Supplemental data
        label = soup.find(text=re.compile('Address:'))
        attributes['address'] = \
            label.parent.parent.findNextSibling('td').contents
            
        label = soup.find(text=re.compile('Telephone:'))
        attributes['telephone'] = \
            label.parent.parent.findNextSibling('td').contents
        
        label = soup.find(text=re.compile('E-mail:'))
        email = label.parent.parent.findNextSibling('td').contents[0]
        
        if hasattr(email, 'contents'):
            attributes['email'] = email.contents
        else:
            if email != 'None':
                attributes['email'] = email
            else:
                attributes['email'] = u''
            
        return attributes        
    
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

    def scrape_bills(self, chamber, year):
        pass
    
if __name__ == '__main__':
    NDLegislationScraper().run()
