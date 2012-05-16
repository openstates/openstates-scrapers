import datetime as dt

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper

import lxml.html
import pytz

url = "http://www.leg.state.mn.us/calendarday.aspx?jday=all"

class MNEventScraper(EventScraper):
    state = 'mn'
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
            datetime = datetime.text_content()
            # Tuesday, June 05, 2012 9:00 AM
            datetime = dt.datetime.strptime(datetime, "%A, %B %d, %Y %I:%M %p")
            event = Event(chamber, datetime, 'committee:meeting',
                          ctty_name, location=metainf['Room:'])
            event.add_source(url)
            self.save_event(event)
