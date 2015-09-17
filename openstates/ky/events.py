import datetime
import re

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
            # Attempt to extract a date string from the most likely DOM element.
            date = div.xpath("string(../preceding-sibling::span[div[@align]][1])").strip()

            try:
                # Get most likely element that contains the event time and location.
                event = div.xpath("string(span[1])")

                # Check whether the event has been cancelled.
                match = re.search(r'\bcance[l]{1,2}ed\b', event, re.IGNORECASE)

                # Skip if the event has been cancelled.
                if match:
                    raise ValueError('Event canceled.')

                # Attempt to separate the time and location.
                delimiter = ','
                time, delimiter, location = event.partition(delimiter)

                # Strip any dates from time string.
                time = re.sub(r'[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}', '', time)

                # Strip extraneous timezone data from time string.
                time = re.sub(r'[\s-]*?([eE][dDsS][tT]).*', '', time)

                time = time.strip()
            except ValueError:
                # No meetings
                continue

            if time == "Noon":
                time = "12:00pm"

            if ':' not in time:
                self.warning('skipping event with invalid time: %s', time)
                continue

            # Combine extracted date and time into a datetime string.
            when = "%s %s" % (date, time)

            # Attempt to create a datetime object from datetime string.
            try:
                when = datetime.datetime.strptime(when, "%A, %B %d, %Y %I:%M%p")
            except ValueError:
                when = datetime.datetime.strptime(when, "%A, %B %d, %Y %I:%M %p")

            # Set the timezone for datetime.
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
