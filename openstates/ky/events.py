import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import lxml.html
import pytz


class KYEventScraper(EventScraper):
    state = 'ky'

    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        if session != '2011 Regular Session':
            raise NoDataForPeriod(session)

        url = "http://www.lrc.ky.gov/legislative_calendar/index.aspx"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for div in page.xpath("//div[@style = 'MARGIN-LEFT: 20px']"):
                date = div.xpath("string(../../span[1])").strip()

                try:
                    time, location = div.xpath("string(span[1])").split(',')
                except ValueError:
                    # No meetings
                    continue

                when = "%s %s" % (date, time)
                when = datetime.datetime.strptime(when,
                                                  "%A, %B %d, %Y %I:%M%p")
                when = self._tz.localize(when)

                desc = div.xpath("string(span[2])").strip()
                event = Event(session, when, 'committee:meeting',
                              desc, location=location)
                event.add_source(url)

                self.save_event(event)
