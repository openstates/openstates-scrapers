import re
import pytz
import datetime
import lxml.html

from billy.scrape.events import EventScraper, Event


class SCEventScraper(EventScraper):
    jurisdiction = 'sc'

    def get_page_from_url(self,url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page
        
    def scrape(self, chamber, session):
        if chamber == 'upper':
            events_url = 'http://www.scstatehouse.gov/meetings.php?chamber=S'
        elif chamber == 'lower':
            events_url = 'http://www.scstatehouse.gov/meetings.php?chamber=H'
        else:
            return

        page = self.get_page_from_url(events_url)
        meeting_year = page.xpath('//h2[@class="barheader"]/span')[0].text_content()
        meeting_year = re.search(r'Week of [A-Z][a-z]+\s+[0-9]{1,2}, ([0-9]{4})', meeting_year).group(1)

        dates = page.xpath("//div[@id='contentsection']/ul")

        for date in dates:
            date_string = date.xpath('span')

            if len(date_string) == 1:
                date_string = date_string[0].text_content()
            else:
                continue

            for meeting in date.xpath('li'):
                time_string = meeting.xpath('span')[0].text_content()

                if time_string == 'CANCELED':
                    continue

                # dynamic meeting times, not sure what to do here
                # examples
                # Upon adjournment of the House
                # 1 1/2 hours after the House adjourns
                if re.search(r'adjourn',time_string):
                    time_string = '12:00 am'

                # if it's a block of time, use the start time
                block_reg = re.compile(r'([0-9]{1,2}:[0-9]{2}) - [0-9]{1,2}:[0-9]{2} ([ap]m)')
                if re.search(block_reg,time_string):
                    start_time, meridiem = re.search(block_reg,time_string).groups()
                    start_hour = int(start_time.split(':')[0])

                    if meridiem == 'pm' and start_hour < 12:
                        time_string = start_time + ' am' 
                    else:
                        time_string = start_time + ' ' + meridiem

                date_time_string = meeting_year + ' ' + date_string + ' ' + time_string
                date_time = datetime.datetime.strptime(date_time_string, "%Y %A, %B %d %I:%M %p")

                meeting_info = meeting.xpath('br[1]/preceding-sibling::node()')[1]

                location, description = re.search(r'-- (.*?) -- (.*)', meeting_info).groups()
                    
                event = Event(
                    session,
                    date_time,
                    'committee:meeting',
                    description,
                    location
                )
                
                event.add_source(events_url)
                    
                agenda_url = meeting.xpath(".//a[contains(@href,'agendas')]")

                if agenda_url:
                    agenda_url = agenda_url[0].attrib['href']
                    event.add_source(agenda_url)
            
                self.save_event(event)


