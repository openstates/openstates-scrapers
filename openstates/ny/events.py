import datetime

from billy.scrape.events import EventScraper, Event

import pytz
import icalendar
import lxml.html


class NYEventScraper(EventScraper):
    state = 'ny'

    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_upper_events(session)
        elif chamber == 'lower':
            self.scrape_lower_events(session)

    def scrape_upper_events(self, session):
        url = ("http://www.nysenate.gov/calendar/ical/"
               "senator%3DAll%2526type%3D3%2526committee%3DAll"
               "%2526initiative%3DAll")

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

    def scrape_lower_events(self, session):
        url = "http://assembly.state.ny.us/leg/?sh=hear"

        year = datetime.date.today().year

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for td in page.xpath("//td[@bgcolor='#99CCCC']"):
                desc = td.xpath("string(following-sibling::td/strong)")
                if 'Senate Standing Committee' in desc:
                    # We should pick these up from the upper scraper
                    continue

                location = td.xpath(
                    "string(../following-sibling::tr[2]/td[2])")

                date = ' '.join(td.text.split()[0:2]).strip()

                time = td.xpath("../following-sibling::tr[3]/td[2]")[0]
                time = time.text.split('-')[0].strip()

                when = "%s %d %s" % (date, year, time)
                when = when.replace('.', '')

                try:
                    when = datetime.datetime.strptime(
                        when, "%b %d %Y %I:%M %p")
                except ValueError:
                    when = datetime.datetime.strptime(
                        when, "%B %d %Y %I:%M %p")

                when = self._tz.localize(when)

                event = Event(session, when, 'committee:meeting',
                              desc, location)
                event.add_source(url)
                self.save_event(event)
