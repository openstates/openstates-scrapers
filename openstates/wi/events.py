import datetime as dt

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper

import lxml.html
import pytz

calurl = "http://committeeschedule.legis.wisconsin.gov/Schedule.aspx"

class WIEventScraper(EventScraper):
    jurisdiction = 'wi'
    _tz = pytz.timezone('US/Eastern')
    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape_page(self, url, chamber, session):
        page = self.lxmlize(url)
        info_blocks = {
            "canceled": "//div[@class='cancelled']",
            "committee": "//div[@class='titlemeetingtype']",
            "chamber": "//div[@class='titlehouse']",
            "datetime": "//div[@class='datetimelocation']"
        }
        metainf = {}
        for block in info_blocks:
            info = page.xpath(info_blocks[block])
            if info == []:
                continue
            metainf[block] = {
                "obj": info[0],
                "txt": info[0].text_content()
            }

        if 'committee' not in metainf:
            return

        if 'canceled' in metainf:
            return

        obj = metainf['datetime']['obj']
        dates = obj.xpath("./*")
        date_time = obj.text.strip()
        for date in dates:
            if date.tail is not None:
                date_time += " %s" % (date.tail.strip())
        # Wednesday, May 23, 2012 10:00 AM 417 North (GAR Hall) State Capitol
        splits = [ 'AM', 'PM' ]
        date_times = None
        for split in splits:
            if split in date_time:
                date_times = [ x.strip() for x in date_time.split(split, 1) ]
                date_times[0] += " " + split

        time = date_times[0]
        place = date_times[1]


        committee = metainf['committee']['txt']

        if not "chamber" in metainf:
            return

        chamber = metainf['chamber']['txt']

        try:
            chamber = {
                "Senate": "upper",
                "Assembly": "lower",
                "Joint": "joint"
            }[chamber]
        except KeyError:
            chamber = 'other'

        # Wednesday, May 23, 2012 10:00 AM
        datetime = dt.datetime.strptime(time, "%A, %B %d, %Y %I:%M %p")
        event = Event(session, datetime, 'committee:meeting',
                      committee, location=place)
        event.add_participant('host', committee, 'committee', chamber=chamber)
        event.add_source(url)
        self.save_event(event)

    def scrape(self, chamber, session):
        if chamber != "other":
            return
        page = self.lxmlize(calurl)
        links = page.xpath("//a[@title]")
        for link in links:
            self.scrape_page(link.attrib['href'], chamber, session)
