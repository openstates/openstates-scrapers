import re
import datetime

from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html


class OHEventScraper(EventScraper):
    state = 'oh'

    _tz = pytz.timezone('US/Central')

    def scrape(self, chamber, session):
        url = "http://www.legislature.state.oh.us/today.cfm"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for td in page.xpath("//td[@bgcolor='FFEAD5' and @height='25']"):
                date = td.text.strip()

                if chamber == 'upper':
                    desc = td.getnext().text.strip()
                else:
                    desc = td.getnext().getnext().text.strip()

                match = re.match(r'^Session at (\d+:\d+ [pa]\.m\.)', desc)
                if match:
                    time = match.group(1)
                    time = time.replace('a.m.', 'AM').replace('p.m.', 'PM')

                    when = "%s 2011 %s" % (date, time)
                    when = datetime.datetime.strptime(when,
                                                      "%a. %b %d %Y %I:%M %p")
                    when = self._tz.localize(when)

                    chamber_name = {'upper': 'Senate',
                                    'lower': 'House'}[chamber]

                    event = Event(session, when, 'floor_time', desc,
                                  "%s Chamber" % chamber_name)
                    event.add_source(url)
                    self.save_event(event)
