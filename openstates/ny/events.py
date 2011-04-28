from billy.scrape.events import EventScraper, Event

import pytz
import icalendar
import lxml.html


class NYEventScraper(EventScraper):
    state = 'ny'

    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        if chamber == 'upper':
            url = ("http://www.nysenate.gov/calendar/ical/"
                   "senator%3DAll%2526type%3D3%2526committee%3DAll"
                   "%2526initiative%3DAll")
        else:
            return

        with self.urlopen(url) as page:
            cal = icalendar.Calendar.from_string(page)

            for comp in cal.walk():
                if comp.name != 'VEVENT':
                    continue

                text = str(comp['SUMMARY'])
                if 'Committee Meeting' not in text:
                    continue

                start = self._tz.localize(comp['DTSTART'].dt)
                end = self._tz.localize(comp['DTEND'].dt)
                uid = str(comp['UID'])
                event_url = comp['URL']

                location = self.get_upper_location(event_url)
                print location

                event = Event(session, start, 'committee:meeting',
                              text, location, end)
                event.add_source(url)
                event.add_source(event_url)

                self.save_event(event)

    def get_upper_location(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            return page.xpath("string(//div[@class = 'adr'])").strip()
