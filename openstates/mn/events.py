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
            print meeting
