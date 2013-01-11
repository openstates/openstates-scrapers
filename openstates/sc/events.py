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
            events_url = 'http://www.scstatehouse.gov/meetings.php?chamber=S&&headerfooter=0'
        elif chamber == 'lower':
            events_url = 'http://www.scstatehouse.gov/meetings.php?chamber=H&headerfooter=0'
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

                # if it's a block, use the start time
                if re.search(r'[0-9]{1,2}:[0-9]{2} - [0-9]{1,2}:[0-9]{2} [ap]m',time_string):
                    start_time = re.search(r'([0-9]{1,2}:[0-9]{2}) - [0-9]{1,2}:[0-9]{2} [ap]m',time_string).group(1)
                    meridiem = re.search(r'[0-9]{1,2}:[0-9]{2} - [0-9]{1,2}:[0-9]{2} ([ap]m)',time_string).group(1)
                    start_hour = int(start_time.split(':')[0])

                    if meridiem == 'pm' and start_hour < 12:
                        time_string = start_time + ' am' 
                    else:
                        time_string = start_time + ' ' + meridiem

                date_time_string = meeting_year + ' ' + date_string + ' ' + time_string
                date_time_obj = datetime.datetime.strptime(date_time_string, "%Y %A, %B %d %I:%M %p")

                #event = Event(
                #	session,
                #	datetime,
                #	'committee:meeting',
                    
                print date_time_string, date_time_obj, meeting
            

