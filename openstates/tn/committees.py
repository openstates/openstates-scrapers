"""
Archived Committee notes:

Senate committees only avail from 105th forward

Urls are inconsistent
'http://www.capitol.tn.gov/senate/archives/105GA/Committees/scommemb.htm'
'http://www.capitol.tn.gov/senate/archives/106GA/Committees/index.html'

'http://www.capitol.tn.gov/house/archives/99GA/Committees/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/100GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/101GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/102GA/Committees/HComm.htm'
'http://www.capitol.tn.gov/house/archives/103GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/104GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/105GA/Committees/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/106GA/Committees/index.html'

"""
import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import Committee, CommitteeScraper
import lxml.html

def fix_whitespace(s):
    return re.sub(r'\s+', ' ', s)

class TNCommitteeScraper(CommitteeScraper):
    state = 'tn'

    base_href = 'http://www.capitol.tn.gov'
    urls = {
        '107': {
            'lower': 'http://www.capitol.tn.gov/house/committees/',
            'upper': 'http://www.capitol.tn.gov/senate/committees/'
        }
    }
    
    
    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        url = self.urls[term][chamber]
        
        if chamber == 'upper':
            self.scrape_senate_committees(url)
        else:
            self.scrape_house_committees(url)

                                        
    def scrape_senate_committees(self, url):
        find_expr = "//dl[@class='senateCommittees']/dt/a"
        
        with self.urlopen(url) as page:
            # Find individual committee urls
            page = lxml.html.fromstring(page)
            
            links = [(a.text_content(), self.base_href + a.attrib['href']) for a in page.xpath(find_expr)]

            # title, url
            for committee_name, link in links:
                self.scrape_senate_committee(committee_name, link)
                

    def scrape_senate_committee(self, committee_name, link):
        """Scrape individual committee page and add members"""
        find_expr = "//div[@class='col1']/ul/li"
        
        com = Committee('upper', committee_name)
        
        with self.urlopen(link) as page:
            # Find individual committee urls
            page = lxml.html.fromstring(page)
            
            for el in page.xpath(find_expr):
                member = [item.strip() for item in el.text_content().split(',',1)]
                if len(member) > 1:
                    member_name, role = member
                else:
                    member_name, role = member[0], 'member'
                    
                if member_name != "":
                    com.add_member(member_name, role)
        
        com.add_source(link)
        self.save_committee(com)


    def scrape_house_committees(self, url):
        # Committees are listed in h3 w/ no attributes. Only indicator is a div w/ 2 classes
        find_expr = "//*[contains(concat(' ', normalize-space(@class), ' '), ' committeelist ')]/h3/a"

        with self.urlopen(url) as page:
            # Find individual committee urls
            page = lxml.html.fromstring(page)
            
            # House links are relative
            links = [(a.text_content(), self.base_href + '/house/committees/' + a.attrib['href']) for a in page.xpath(find_expr)]

            for committee_name, link in links:
                self.scrape_house_committee(committee_name, link)


    def scrape_house_committee(self, committee_name, link):
        """Scrape individual committee page and add members"""
        find_expr = "//div[@class='col1']/ul/li"
        
        com = Committee('lower', committee_name)
        
        with self.urlopen(link) as page:
            # Find individual committee urls
            page = lxml.html.fromstring(page)
            
            for el in page.xpath(find_expr):
                member = [item.strip() for item in el.text_content().split(',',1)]
                if len(member) > 1:
                    member_name, role = member
                else:
                    member_name, role = member[0], 'member'
                    
                if member_name != "":
                    com.add_member(member_name, role)

        
        com.add_source(link)
        self.save_committee(com)
