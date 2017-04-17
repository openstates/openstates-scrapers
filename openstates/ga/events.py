import re
import pytz
import datetime
import lxml.html

from billy.scrape.events import EventScraper, Event

class GAEventScraper(EventScraper):
    jurisdiction = 'ga'
    _tz = pytz.timezone('US/Eastern')

    def get_page_from_url(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def normalize_time(self, meeting_time):

        meeting_time = meeting_time.lower()

        if meeting_time == 'tbd':
            meeting_time = '12:00 am'

        if re.search('^[0-9]+:[0-9]+ [ap]m', meeting_time):
            meeting_time = re.search('^([0-9]+:[0-9]+ [ap]m)', meeting_time).group(1)

        return meeting_time

    def scrape(self, chamber, session):

        if chamber == 'other':
            return

        events_url = 'http://webmail.legis.ga.gov/Calendar/default.aspx?chamber=%s' % (self.metadata['chambers'][chamber]['name'].lower())

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

                meeting_time = self.normalize_time(row.xpath('.//td[@class="cssItemTimeCell"]')[0].text_content().strip())
                meeting_time = datetime.datetime.strptime(date_string + ' ' + meeting_time, '%A, %B %d, %Y %I:%M %p')
                meeting_time = self._tz.localize(meeting_time)

                subject_info = row.xpath('.//a[@class="cssItemsSubjectHyperLink"]')
                description = subject_info[0].text_content().strip()
                meeting_url = subject_info[0].attrib['href'].strip()

                location = row.xpath('string(.//td[@class="cssItemLocationCell"])').strip()

                if re.search('floor session', description, re.I):
                    continue

                event = Event(
                    session, 
                    meeting_time, 
                    'committee:meeting',
                    description,
                    location,
                )

                event.add_source(meeting_url)
                self.save_event(event)

