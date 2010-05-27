#!/usr/bin/env python
import datetime
import os
import re
import sys
import html5lib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear, ScrapeError)


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
        'upper_term': 4,
        'lower_term': 4,
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
        
        # No legislator data for 1997 (though other data is available)
        if year == '1997':
            raise NoDataForYear(year)
        
        # URL building
        if chamber == 'upper':
            url_chamber_name = 'senate'
            norm_chamber_name = 'Senate'
            url_member_name = 'senators'
        else:
            url_chamber_name = 'house'
            norm_chamber_name = 'House'
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
        
        party_images = {'/images/donkey.gif': 'Democrat', '/images/elephant.gif': 'Republican'}
        for row in header.findNextSibling('table').findAll('tr'):
            cells = row.findAll('td')
            party = party_images[cells[0].img['src']]
            name = map(lambda x: x.strip(), cells[1].a.contents[0].split(', '))
            name.reverse()
            name = ' '.join(name)
            district = re.findall('District (\d+)', cells[2].contents[0])[0]
            attributes = {
                'session': year,
                'chamber': chamber,
                'district': district,
                'party': party,
                'full_name': name,
            }
            split_name = name.split(' ')
            if len(split_name) > 2:
                attributes['first_name'] = split_name[0]
                attributes['middle_name'] = split_name[1].strip(' .')
                attributes['last_name'] = split_name[2]
            else:
                attributes['first_name'] = split_name[0]
                attributes['middle_name'] = u''
                attributes['last_name'] = split_name[1]

            # we can get some more data..
            bio_url = self.site_root + cells[1].a['href']
            try:
                attributes.update(self.scrape_legislator_bio(bio_url))
            except urllib2.HTTPError: 
                self.log("failed to fetch %s" % bio_url)

            self.debug("attributes: %d", len(attributes))
            self.debug(attributes)
            # Save
            legislator = Legislator(**attributes)
            legislator.add_source(bio_url)
            self.save_legislator(legislator)
    
    def scrape_legislator_bio(self, url):
        """
        Scrape the biography page of a specific ND legislator.
        
        Note that some parsing is conditional as older bio pages are not
        formatted exactly as more recent ones are.
        """
        # Parsing
        try:
            data = self.urlopen(url)
        except: 
            return {}
        soup = self.parser.parse(data)
        
        attributes = {}
   
        # Supplemental data
        label = soup.find(text=re.compile('Address:'))
        attributes['address'] = \
            label.parent.parent.findNextSibling('td').contents[0]
            
        label = soup.find(text=re.compile('Telephone:'))
        try:
            attributes['telephone'] = \
                label.parent.parent.findNextSibling('td').contents[0]
        except:
            # Handle aberrant empty tag
            attributes['telephone'] = u''
        
        label = soup.find(text=re.compile('E-mail:'))
        try:
            email = label.parent.parent.findNextSibling('td').contents[0]
        except:
            email = u''
        
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
        else:
            url_chamber_name = 'house'
            norm_chamber_name = 'House'
        
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
        indexed_bills = {}
        
        self.log('Scraping %s bills for %s.' % (norm_chamber_name, year))
        
        for link in bill_links:
            # Populate base attributes
            attributes = {
                'session': year,
                'chamber': chamber,
                }
            
            bill_number = link.contents[0]
            
            if not re.match('^[0-9]{4}$', bill_number):
                raise ScrapeError('Bill number not in expected format.')
            
            # ND bill prefixes are coded numerically
            if bill_number[0] == '1':
                bill_prefix = 'HB'
            elif bill_number[0] == '2':
                bill_prefix = 'SB'
            elif bill_number[0] == '3':
                bill_prefix = 'HCR'
            elif bill_number[0] == '4':
                bill_prefix = 'SCR'
            elif bill_number[0] == '5':
                bill_prefix = 'HR'
            elif bill_number[0] == '6':
                bill_prefix = 'SR'
            elif bill_number[0] == '7':
                bill_prefix = 'HMR'
            elif bill_number[0] == '8':
                bill_prefix = 'SMR'
                
            attributes['bill_id'] = bill_prefix + ' ' + bill_number
            
            # Skip duplicates (bill is listed once for each version)
            if attributes['bill_id'] in indexed_bills.keys():
                continue
            
            self.debug(attributes['bill_id'])
            
            # Parse details page                
            attributes.update(
                self.scrape_bill_details(assembly_url, bill_number))
        
            # Create bill
            bill = Bill(**attributes)
            
            # Parse actions      
            (actions, actions_url) = self.scrape_bill_actions(
                assembly_url, bill_number, year)
            bill.add_source(actions_url)
            
            for action in actions:
                bill.add_action(**action)

            # Parse versions
            (versions, versions_url) = self.scrape_bill_versions(
                assembly_url, bill_number)
            bill.add_source(versions_url)
            
            for version in versions:
                bill.add_version(**version)
            
            # Add bill to dictionary, indexed by its id
            indexed_bills[attributes['bill_id']] = bill
        
        # Parse sponsorship data
        if int(year) >= 2005:
            self.log('Scraping sponsorship data.')
            
            (sponsors, sponsors_url) = self.scrape_bill_sponsors(assembly_url)
            
            for bill_id, sponsor_list in sponsors.items():
                for sponsor in sponsor_list:
                    # Its possible a bill was misnamed somewhere... but thats
                    # not a good enough reason to error out
                    if bill_id in indexed_bills.keys():
                        bill = indexed_bills[bill_id]
                        bill.add_sponsor(**sponsor)
                        bill.add_source(sponsors_url)
        else:
            self.log('Sponsorship data not available for %s.' % year)
                
        self.log('Saving scraped bills.')
        
        # Save bill
        for bill in indexed_bills.values():
            self.save_bill(bill)
            
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
        
        # There is at least one page that contains no valid data: 2001 / SB2295
        if not table:
            return { 'title': u''}
        
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
        
        # There is at least one page that contains no valid data: 2001 / SB2295
        if not table:
            return []
        
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
                actor = actor_cell.contents[0].strip()
                if actor == 'Senate':
                    actor = u'upper'
                elif actor == 'House':
                    actor = u'lower'
                
            action['actor'] = actor
                
            action_cell = actor_cell.nextSibling.nextSibling.nextSibling.nextSibling
            
            action['action'] = action_cell.contents[0].replace('\n', '')
            
            actions.append(action)
            
        return (actions, url)
    
    def scrape_bill_versions(self, assembly_url, bill_number):
        """
        Scrape URLs from the versions page of a specific ND bill.
        
        TODO: parse Fiscal Notes
        e.g. http://www.legis.nd.gov/assembly/61-2009/bill-index/bi4038.html
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
            
        return (versions, url)
    
    def scrape_bill_sponsors(self, assembly_url):
        """
        Scrape a list of all bill sponsers for a given year and chamber.
        
        Sponsers can not be accurately scraped from the bill details page,
        so instead they are scraped from an index by member/committee.
        
        Each sponser is buffered into a list which is set as the value in
        a dictionary, with the bill id as the key.  This dictionary is passed
        back to the main scraping method to be appended to the bill
        attributes.
        """        
        url = \
            self.site_root + \
            assembly_url + \
            '/sponsor-inquiry/index.html'
        
        # Parsing
        soup = self.parser.parse(self.urlopen(url))
        
        bill_sponsors = {}
        
        container = soup.find('div', id='content')
        categories = container.findAll('dl')
        
        for category in categories:
            links = category.findAll('a')
            
            for link in links:            
                detail_url = \
                    self.site_root + \
                    assembly_url + \
                    '/sponsor-inquiry/' + \
                    link['href']
                
                if re.match('(Senator|Representative) (.*)', link.contents[0]):
                    name_match = \
                        re.match('(Senator|Representative) (.*)', link.contents[0])
                    member_name =  name_match.group(2).strip()
                else:
                    member_name = link.contents[0]
                
                detail_soup = self.parser.parse(self.urlopen(detail_url))
                
                # Bills for which the member was a primary sponsor
                div = detail_soup.find('div', id='content')
                
                primary_bills = div.dl.findAll('dt')
                
                for bill in primary_bills:
                    bill_id = bill.a.contents[0]
                    sponsor = {'type': u'primary', 'name': member_name}
                    
                    if bill_id in bill_sponsors.keys():
                        bill_sponsors[bill_id].append(sponsor)
                    else:
                        bill_sponsors[bill_id] = [sponsor]
                
                # Bills for which the member was a cosponsor
                # (committees will not have this table)
                if div.table:
                    cosponsor_bills = div.table.findAll('dt')
                    
                    for bill in cosponsor_bills:
                        bill_id = bill.a.contents[0]
                        sponsor = {'type': u'cosponsor', 'name': member_name} 
                        
                        if bill_id in bill_sponsors.keys():
                            bill_sponsors[bill_id].append(sponsor)
                        else:
                            bill_sponsors[bill_id] = [sponsor]            
    
        return (bill_sponsors, url)
    
if __name__ == '__main__':
    NDLegislationScraper.run()
