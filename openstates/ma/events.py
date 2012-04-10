import re
import datetime as dt

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper

import pytz
import lxml.html

urls = "http://www.malegislature.gov/Events/%s"
pages = {
    "lower" : [ urls % "SenateSessions" ],
    "upper" : [ urls % "HouseSessions" ],
    "other" : [ urls % "JointSessions",
                urls % "Hearings", urls % "SpecialEvents" ]
}

class MAEventScraper(EventScraper):
    state = 'ma'

    _tz = pytz.timezone('US/Eastern')

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def parse_row(self, row):
        dates = row.xpath("./td[@class='dateCell']")
        for date in dates:
            # alright, so we *may* not get a date, in which case the date
            # is the same as the last event.
            cal_date = date.xpath("./span[@class='calendarMonth']")[0]
            cal_day = date.xpath("./span[@class='calendarDay']")[0]
            self.last_month = cal_date.text_content()
            self.last_day = cal_day.text_content()
        time = row.xpath("./td[@class='timeCell']")
        if not time:
            return  # Nada.
        time = time[0]
        time = time.text.strip()
        dt_string = "%s %s %s %s" % (
            self.last_month,
            self.last_day,
            self.year,
            time
        )
        fmt = "%b %d %Y %I:%M %p"
        when = dt.datetime.strptime(dt_string, fmt)
        print when

    def scrape(self, chamber, session):
        scrape_list = pages[chamber]
        self.year = dt.datetime.now().year
        for site in scrape_list:
            page = self.lxmlize(site)
            rows = page.xpath("//tbody[not(contains(@id, 'noDates'))]/tr[contains(@class, 'dataRow')]")
            for row in rows:
                self.parse_row(row)
