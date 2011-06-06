import re
import datetime

from billy.scrape.events import EventScraper, Event

import lxml.html


class OKEventScraper(EventScraper):
    state = 'ok'

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_upper(session)

    def scrape_upper(self, session):
        url = "http://www.oksenate.gov/Committees/meetingnotices.htm"
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Meeting_Notice')]"):
            comm = link.text.strip()
            comm = re.sub(r'\s+', ' ', comm)

            if link.getnext().text == 'Cancelled':
                continue

            date_path = "../../preceding-sibling::p[@class='MsoNormal']"
            date = link.xpath(date_path)[-1].xpath("string()")

            time_loc = link.xpath("../br")[0].tail.strip()
            time = re.match("\d+:\d+ (am|pm)", time_loc).group(0)
            location = time_loc.split(', ')[1].strip()

            dt = "%s %s" % (date, time)
            dt = datetime.datetime.strptime(dt, "%A, %B %d, %Y %I:%M %p")

            event = Event(session, dt, 'committee:meeting',
                          "%s Committee Meeting" % comm,
                          location)
            event.add_source(url)
            self.save_event(event)
