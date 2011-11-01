import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper

import pytz
import lxml.html


class MAEventScraper(EventScraper):
    state = 'ma'

    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        if session != '187th':
            raise NoDataForPeriod(session)

        #Currently this code only supports 2011
        year = '2011'
        
        #Search by event type. [post attribute, name]
        event_type_list = [['Joint','joint:session'],
                           ['House','house:session'],
                           ['Senate','senate:session'],
                           ['Hearings','committee:hearing'],
                           ['SpecialEvents','special'],
                           ['Redistricting','redistricting']]
        
        for event_type in event_type_list:
            print event_type[0]
            url = "http://www.malegislature.gov/Events/Search"
            input_string = "Input.%s=true&" % event_type[0]
            post_data = (input_string +
                         "Input.StartDate=1%2F1%2F2011&"
                         "Input.EndDate=12%2F31%2F2011")

            with self.urlopen(url, 'POST', post_data) as page:
                page = lxml.html.fromstring(page)
                page.make_links_absolute(url)
                
                path = "//div[@id='eventsTable']/table//tr"
                for row in page.xpath(path)[2:]:
                    cells = row.xpath('./td')
                    
                    #td class='dateCell'
                    if len(cells) == 7:
                        month = cells[0].xpath('string(span[2])')
                        day = cells[0].xpath('string(span[3])')
                        del cells[0]
                        
                    #td class='timeCell'
                    time = cells[0].text.strip()
                    when = datetime.datetime.strptime(
                            month+' '+day+' '+time+' '+year,
                                                      "%b %d %I:%M %p %Y")
                    when = self._tz.localize(when)

                    #td class='eventCell'
                    description = cells[1].xpath('string(./a)').strip()
                    link = cells[1].xpath(
                            'string(./a/attribute::href)').strip()
                    
                    #td class='locationCell'
                    where_name = cells[3].xpath('string(./a)').strip()
                    loc = cells[3].xpath(
                            'string(./a/attribute::href)').strip()
                    try:
                        where_address = re.search('daddr=(.*)', loc).group(1)
                    except:
                        where_address = ""
                    where = where_name + ", " + where_address
                    
                    event = Event(session, when, event_type[1],
                                  description, location=where)
                    event.add_source(url)
                    event['link'] = link
                    self.save_event(event)
