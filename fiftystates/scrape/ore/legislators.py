from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.ore.utils import chambers_url, legs_url, year_from_session

import lxml.html
import re, csv, urllib

class ORELegislatorScraper(LegislatorScraper):
    state = 'or'

    def scrape(self, chamber, session):
        if year_from_session(session) != 2010:
            raise NoDataForPeriod(session)
        
        if chamber == 'upper':
            url_piece = 'senate'
            url_piece2 = 'senator'
        else:
            url_piece = 'house'
            url_piece2 = 'representative'           
        
        chamber_url = chambers_url(url_piece)
        
        leg_reader = csv.reader(urllib.urlopen(chamber_url))
        
        with self.urlopen(legs_url(url_piece2)) as leg_page_html:
            leg_page = lxml.html.fromstring(leg_page_html)
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
            leg = Legislator(session, chamber, district, name_and_party[0], row[1], row[2], "", name_and_party[1], \
                              capitol_address=row[3], capitol_phone=row[4], district_adress=row[5], \
                              district_phone=row[6], session_email=row[7])
            self.save_legislator(leg)
            
        
