
import re
import datetime
import itertools
from billy.scrape import NoDataForPeriod,ScrapeError
from billy.scrape.events import Event, EventScraper

import pytz
import lxml.html
import feedparser


class PREventScraper(EventScraper):
    state = 'pr'

    _tz = pytz.timezone('US/Alaska')
    
    def scrape(self, chamber, session):
        if chamber == 'lower':
            raise ScrapeError('parser not implemented yet.')
        
        self.upper_url = 'http://www.senadopr.us/Lists/Calendario%20Legislativo/DispForm_original.aspx?ID='#29 is the start number for the counter <_<
        self.lower_url = 'http://www.camaraderepresentantes.org/cr_calendario.asp?d=3/28/2007'# % 
        counter = itertools.count(29)
        for event_id in counter:
            
            self.scrape_events(chamber, session,event_id)
            
        #year, year2 = None, None
        #for term in self.metadata['terms']:
            #if term['sessions'][0] == session:
                #year = str(term['start_year'])
                #year2 = str(term['end_year'])
                #break

    def scrape_events(self, chamber,session,event_id):
        url = '%s%s' % (self.upper_url, event_id)
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)
            rows = doc.xpath("//div[@id='WebPartWPQ2']")
            #some ids are empty 
            if len( rows):
                table_data = rows[0].find('table')[1]
                
                for link in table_data.iterchildren('td'):
                    td = link.xpath('//td[@class="ms-formbody"]')
                    #for hai  in td:
                        #print hai.text
                    description =  td[18].text
                    when =  td[19].text
                    
                    print td[21].text
                    print td[22].text
                    print td[22].text
                    print td[24].text
                    where = td[25].text
                    print td[26].text
                    type = td[27].text
                    meeting_lead =  td[28].text
                    print td[29].text
                    print td[29].text
                    
                             
                            
                    when = datetime.datetime.strptime(when, "%m/%d/%Y  %H:%M %p")
                    when = self._tz.localize(when)
                    event_type = 'committee:meeting';
                    event = Event(session, when, event_type,
                                    description, location=where)
                    if td[20].text is None:
                        participants = meeting_lead
                    else:
                        participants = td[20].text.split(';')
                    if participants:
                        for participant in participants:
                            event.add_participant('committee',participant.strip().replace('HON.','',1));
                    event.add_source(url)
                    self.save_event(event)
                    