
import re
import datetime
import itertools
from billy.scrape import NoDataForPeriod,ScrapeError
from billy.scrape.events import Event, EventScraper
from lxml import etree
import pytz
import lxml.html
import feedparser


class PREventScraper(EventScraper):
    state = 'pr'

    _tz = pytz.timezone('US/Alaska')
    
    
    def daterange(self,start_date, end_date):
        for n in range((end_date - start_date).days):
            yield start_date + datetime.timedelta(n)
            
    def scrape_lower_events(self, chamber, session):
        print session
        start_day = datetime.date(2009, 1, 1);
        #start_day = datetime.date(2009, 2, 21);
        for day in self.daterange(start_day,datetime.date(2012, 12, 31)):
            when = day.strftime('%m/%d/%Y')
            url = '%s%s' % (self.lower_url, when);
            with self.urlopen(url) as html:
                doc = lxml.html.fromstring(html)
                doc.make_links_absolute(url)
                rows = doc.xpath("//div[@style='background-color:#C1BBAD; font-size:11pt;width:100%;text-align:left;padding:0px;color:#ffffff;']");
                for event_se in rows:
                    #comittiiee name
                    #print event_block.xpath('b')[0].text
                    #legislator
                    #author = event_block.xpath('../i')
                    #if len(author) > 0:
                        #print author[0].text
                    #time
                    hour =  event_se.xpath('../div/table/tr/td')[1].xpath('b/i')[0].text
                    hour = hour.encode('ascii', 'ignore').replace(" ","");
                    
                    description = event_se.xpath('../div')[1].text
                    event_type = ''
                    if 'Vista Pubilca' == description or description == 'Vista Publica' or 'Vista Pblica' == description:
                        event_type = 'committee:meeting';
                    elif 'Vista Ejecutiva' == description:
                        event_type = 'committee:meeting';
                    elif 'Vista Ocular' == description:
                        event_type = 'committee:meeting';
                    else:
                        event_type = 'committee:other'
                    time  = datetime.datetime.strptime(when + hour, '%m/%d/%Y%I:%M%p')
                    where = event_se.xpath('../div/table/tr/td')[0].xpath('b/i')[0].text
                    event = Event(session, time, event_type, description, location=where)
                    event.add_source(url)
                    self.save_event(event)   
            
    def scrape_upper_events(self, chamber, session):
        counter = itertools.count(29)
        for event_id in counter:
            try:
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
                            
                            description =  td[18].text
                            when =  td[19].text
                            where = td[25].text
                            type = td[27].text
                            meeting_lead =  td[28].text
                            
                            when = datetime.datetime.strptime(when, "%m/%d/%Y  %H:%M %p")
                            when = self._tz.localize(when)
                            event_type = 'committee:meeting';
                            event = Event(session, when, event_type, description, location=where)
                            
                            if td[20].text is None:
                                participants = meeting_lead
                            else:
                                participants = td[20].text.split(';')
                            if participants:
                                for participant in participants:
                                    event.add_participant('committee',participant.strip().replace('HON.','',1));
                            
                            event.add_source(url)
                            self.save_event(event)
                    else :
                        #hack so we dont fail on the first id numbers where there are some gaps between the numbers that work and not.
                        if event_id > 2000:
                            raise ScrapeError("Parsing is done we are on future ids that are not used yet.")
            except ScrapeError:
                break
                
    def scrape(self, chamber, session):
       
        self.upper_url = 'http://www.senadopr.us/Lists/Calendario%20Legislativo/DispForm_original.aspx?ID='#29 is the start number for the counter <_<
        self.lower_url = 'http://www.camaraderepresentantes.org/cr_calendario.asp?d='
        if chamber == 'lower':
            self.scrape_lower_events(chamber,session);
        elif chamber == 'upper':
            self.scrape_upper_events(chamber,session);