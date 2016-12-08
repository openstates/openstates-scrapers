
import re
import datetime
import itertools
from billy.scrape import NoDataForPeriod,ScrapeError
from billy.scrape.events import Event, EventScraper

import pytz
import lxml.html
import feedparser


class PREventScraper(EventScraper):
    jurisdiction = 'pr'

    _tz = pytz.timezone('US/Alaska')

    def scrape(self, chamber, session):
        if chamber == 'lower':
            return

        self.upper_url = 'http://www.senadopr.us/Lists/Calendario%20Legislativo/DispForm_original.aspx?ID='#29 is the start number for the counter <_<
        self.lower_url = 'http://www.camaraderepresentantes.org/cr_calendario.asp?d=3/28/2007'# %
        counter = itertools.count(29)
        for event_id in counter:
            try:
                self.scrape_events(chamber, session,event_id)
            except ScrapeError:
                break

        #year, year2 = None, None
        #for term in self.metadata['terms']:
            #if term['sessions'][0] == session:
                #year = str(term['start_year'])
                #year2 = str(term['end_year'])
                #break

    def scrape_events(self, chamber,session,event_id):
        url = '%s%s' % (self.upper_url, event_id)
        html = self.get(url).text
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
                kwargs = { "location" : "State House" }
                if where is not None and where != "":
                    kwargs['location'] = where
                event = Event(session, when, event_type, description, **kwargs)

                if td[20].text is None:
                    participants = meeting_lead
                else:
                    participants = td[20].text.split(';')
                if participants:
                    for participant in participants:
                        name = participant.strip().replace('HON.','',1)
                        if name != "":
                            event.add_participant('committee',
                                                  name,
                                                  'committee',
                                                  chamber=chamber)

                event.add_source(url)
                self.save_event(event)
        else :
            #hack so we dont fail on the first id numbers where there are some gaps between the numbers that work and not.
            if event_id > 1700:
                raise ScrapeError("Parsing is done we are on future ids that are not used yet.")
