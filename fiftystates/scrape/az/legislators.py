from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from lxml import html

import re, datetime

class AZLegislatorScraper(LegislatorScraper):
    state = 'az'
    parties = {
        'R': 'Republican',
        'D': 'Democrat',
        'L': 'Libertarian',
        'I': 'Independant',
        'G': 'Green'
    }
    
    def get_party(self, abbr):
        return self.parties[abbr]
        
    def get_session_id(self, session):
        return self.metadata['session_details'][session]['session_id']
        
    def get_session_for_term(self, term):
        # ideally this should be either first or second regular session
        # and probably first and second when applicable
        for t in self.metadata['terms']:
            if t['name'] == term:
                session = t['sessions'][-1]
                if re.search('Regular', session):
                    return session
                else:
                    return t['sessions'][0]
                
    def scrape(self, chamber, term):
        self.validate_term(term)
        session = self.get_session_for_term(term)
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod(session)
            
        body = {'lower': 'H', 'upper': 'S'}[chamber]
        url = 'http://www.azleg.gov/MemberRoster.asp?Session_ID=%s&body=%s' % (
                                                               session_id, body)
        with self.urlopen(url) as page:
            root = html.fromstring(page)
            path = '//table[@id="%s"]/tr' % {'H': 'house', 'S': 'senate'}[body]
            roster = root.xpath(path)[1:]
            for row in roster:
                position = ''
                vacated = ''
                name, district, party, email, room, phone, fax = row.getchildren()
                
                link = name.xpath('string(a/@href)')
                if len(name) == 1:
                    name = name.text_content().strip()
                else:
                    position = name.tail.strip()
                    name = name[0].text_content().strip()
                    
                district = district.text_content()
                party = party.text_content().strip()
                party = self.get_party(party)
                email = email.text_content().strip()
                
                if re.match('Vacated', email):
                    vacated = re.search('[0-9]*/[0-9]*/\d{4}', email).group()
                    email = ''
                
                room = room.text_content().strip()
                phone = phone.text_content().strip()
                if not phone.startswith('602'):
                    phone = "602-" + phone
                fax = fax.text_content().strip()
                if not fax.startswith('602'):
                    fax = "602-" + fax
                if vacated:
                    end_date = datetime.datetime.strptime(vacated, '%m/%d/%Y')
                    leg = Legislator( term, chamber, district, full_name=name,
                                      party=party, url=link)
                    leg['roles'][0]['end_date'] = end_date
                else:
                    leg = Legislator( term, chamber, district, full_name=name,
                                      party=party, phone=phone, fax=fax, room=room, 
                                      email=email, url=link)
                
                if position:
                    leg.add_role( position, term, chamber=chamber, 
                                 district=district, party=party)
                      
                leg.add_source(url)
                
                #Probably just get this from the committee scraper
                #self.scrape_member_page(link, session, chamber, leg)
                self.save_legislator(leg)
                
    def scrape_member_page(self, url, session, chamber, leg):
        with self.urlopen(url) as member_page:
            root = html.fromstring(member_page)
            #get the committee membership
            c = root.xpath('//td/div/strong[contains(text(), "Committee")]')
            for row in c.xpath('ancestor::table[1]')[1:]:
                name = row[0].text_content().strip()
                role = row[1].text_content().strip()
                leg.add_role(role, session, chamber=chamber, committee=name)
                        
            leg.add_source(url)       
