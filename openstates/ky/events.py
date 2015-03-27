import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import lxml.html
import pytz


class KYEventScraper(EventScraper):
    jurisdiction = 'ky'

    _tz = pytz.timezone('US/Eastern')

    def scrape(self, session, chambers):
        url = "http://www.lrc.ky.gov/legislative_calendar/index.aspx"
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        for div in page.xpath("//div[@style = 'MARGIN-LEFT: 20px']"):
            date = div.xpath("string(../../span[1])").strip()

            try:
                time, location = div.xpath("string(span[1])").split(',')
            except ValueError:
                # No meetings
                continue

            if time == "Noon":
                time = "12:00pm"

            if ':' not in time:
                self.warning('skipping event with invalid time: %s', time)
                continue
            when = "%s %s" % (date, time)
            try:
                when = datetime.datetime.strptime(when, "%A, %B %d, %Y %I:%M%p")
            except ValueError:
                when = datetime.datetime.strptime(when, "%A, %B %d, %Y %I:%M %p")

            when = self._tz.localize(when)

            desc = div.xpath("string(span[2])").strip()
            agenda = div.xpath("string(span[3])").strip()
            # XXX: Process `agenda' for related bills.
            if desc.lower().strip() in ["house convenes","senate convenes"]:
                continue

            event = Event(session, when, 'committee:meeting',
                          desc, location=location)
            event.add_source(url)

            # desc is actually the ctty name.
            if "house" in desc.lower():
                chamber = "lower"
            elif "senate" in desc.lower():
                chamber = "upper"
            elif "joint" in desc.lower():
                chamber = "joint"
            else:
                self.logger.warning("Event %s chamber is unknown, skipping" % desc)
                continue

            event.add_participant('host', desc, 'committee', chamber = chamber)

            self.save_event(event)
