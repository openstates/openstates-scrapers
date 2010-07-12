from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import re, contextlib, csv, urllib

class ORLegislatorScraper(LegislatorScraper):
    state = 'or'
    
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
            print "FAIL"
            #self.show_error(url, body)
            raise

    def scrape(self, chamber, year):
        if chamber == 'upper':
            url_piece = 'senate'
            url_piece2 = 'senator'
        else:
            url_piece = 'house'
            url_piece2 = 'representative'           
        
        chamber_url = 'http://www.leg.state.or.us/' + url_piece + '/' + url_piece + '.csv'
        
        leg_reader = csv.reader(urllib.urlopen(chamber_url))
        
        url = 'http://www.leg.state.or.us/servlet/XSLT?URL=members.xml&xslURL=members.xsl&member-type=' + url_piece2
        
        with self.lxml_context(url) as leg_page:
            font_elements = leg_page.cssselect('font')
            names = {}
            for fe in font_elements:
                name_elements = fe.cssselect('a')
                for ne in name_elements:
                    if 'Senator' in ne.text_content() or 'Representative' in ne.text_content():
                        break
                    name_and_party_list = ne.text_content().split('-')
                    names[name_and_party_list[0]] = name_and_party_list[1]
                    
            district_matches = re.findall("District: ([0-9]+)", leg_page.text_content())
        
        # Title,First Name,Last Name,Capitol Address,Capitol Phone,District Address,District Phone,Session Email
        for row, district, name_and_party in zip(leg_reader, district_matches, names.iteritems()):
            leg = Legislator(year, chamber, district, name_and_party[0], row[1], row[2], "", name_and_party[1], \
                              capitol_address=row[3], capitol_phone=row[4], district_adress=row[5], \
                              district_phone=row[6], session_email=row[7])
            self.save_legislator(leg)
            
        
