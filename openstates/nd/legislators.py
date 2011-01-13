import datetime
import re
import html5lib

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.legislators import Legislator, LegislatorScraper
from openstates.nd import metadata

class NDLegislatorScraper(LegislatorScraper):
    """
    Scrapes available legislator information from the website of the North
    Dakota legislature and stores it in the fiftystates backend.
    """
    state = 'nd'
    site_root = 'http://www.legis.nd.gov'
    parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup'))
    
    
    def scrape(self, chamber, year):
        """
        Scrape the ND legislators seated in a given chamber during a given year.
        """    
        # Error checking
        if year not in metadata['session_details']:
            raise NoDataForPeriod(year)
        
        # No legislator data for 1997 (though other data is available)
        if year == '1997':
            raise NoDataForPeriod(year)
        
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
            metadata['session_details'][str(year)]['number'],
            year,
            url_chamber_name)
        
        list_url = \
            self.site_root + \
            assembly_url + \
            '/members/last-name.html'    
        
        # Parsing
        with self.urlopen(list_url) as data:
            soup = self.parser.parse(data)
            
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

