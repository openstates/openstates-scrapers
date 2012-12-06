import datetime as dt

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper

import lxml.html
import pytz

url = "http://www.leg.state.mn.us/calendarday.aspx?jday=all"

class MNEventScraper(EventScraper):
    jurisdiction = 'mn'
    _tz = pytz.timezone('US/Eastern')
    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape(self, chamber, session):
        if chamber != "other":
            return None
        page = self.lxmlize(url)
        meetings = page.xpath("//div[@class='Comm_item']")
        for meeting in meetings:
            metas = meeting.xpath(".//b")
            ctty = meeting.xpath(".//a")[0]
            ctty_name = ctty.text_content()
            info = metas[1:]
            datetime = metas[0]
            metainf = {}
            for meta in info:
                header = meta.text_content().strip()
                val = meta.tail
                metainf[header] = val or ""
            datetime = datetime.text_content().strip()
            # Tuesday, June 05, 2012 9:00 AM
            if "Canceled" in datetime:
                continue

            formats = [
               "%A, %B %d, %Y %I:%M %p",
               "%A, %B %d, %Y"
            ]
            date_time = None

            for fmt in formats:
                try:
                    date_time = dt.datetime.strptime(
                        datetime, fmt)
                except ValueError:
                    pass

            if date_time is None:
                continue

            event = Event(session,
                          date_time,
                          'committee:meeting',
                          ctty_name,
                          location=metainf['Room:'] or "State House",
                          chamber=chamber
                         )
            event.add_source(url)

            if metainf['Chair:'] != "":
                event.add_participant('chair', metainf['Chair:'], 'legislator',
                                      chamber=chamber)

            chamber = "other"
            chambers = {
                "house": "lower",
                "joint": "joint",
                "senate": "upper",
            }
            for c in chambers:
                if c in ctty_name.lower():
                    chamber = chambers[c]

            event.add_participant('host', ctty_name, 'committee', chamber=chamber)
            # add chair?

            self.save_event(event)
