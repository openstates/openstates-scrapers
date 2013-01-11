import re
import datetime
import lxml.html
from billy.scrape.events import EventScraper, Event

class GAEventScraper(EventScraper):
    jurisdiction = 'ga'

    def get_page_from_url(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape(self, chamber, session):
        if chamber == 'upper':
            events_url = 'http://webmail.legis.ga.gov/Calendar/default.aspx?chamber=senate'
        elif chamber == 'lower':
            events_url = 'http://webmail.legis.ga.gov/Calendar/default.aspx?chamber=house'
        else:
            return 

        page = self.get_page_from_url(events_url)
        rows = page.xpath("//table[@id='tblItems']/tr")

        date_string = None

        for row in rows:

            if row.attrib['class'] == 'cssItemHeaderRow':
                continue
            elif row.attrib['class'] == 'cssItemsDayRow':
                date_string = row.text_content().strip()
                continue
            elif row.attrib['class'] in ('cssItemsRowDark', 'cssItemsRowLight'):

                meeting_time = row.xpath('./td[@class="cssItemTimeCell"]')[0].text_content().strip()
                (start_time, end_time,) = meeting_time.split(' - ')
                start_date_time = datetime.datetime.strptime(date_string + ' ' + start_time, '%A, %B %d, %Y %I:%M %p')
                end_date_time = datetime.datetime.strptime(date_string + ' ' + end_time, '%A, %B %d, %Y %I:%M %p')

                subject_info = row.xpath('.//a[@class="cssItemsSubjectHyperLink"]')
                description = subject_info[0].text_content().strip()
                meeting_url = subject_info[0].attrib['href'].strip()
                location = row.xpath('string(//td[@class="cssItemLocationCell"])').strip()

                event = Event(
                    session, 
                    start_date_time, 
                    'committee:meeting',
                    description,
                    location,
                    end=end_date_time
                )

                event.add_source(meeting_url)
                self.save_event(event)

