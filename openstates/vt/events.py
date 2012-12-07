import datetime as dt

from billy.scrape.events import Event, EventScraper

import pytz
import lxml.html

class VTEventScraper(EventScraper):
    jurisdiction = 'vt'

    _tz = pytz.timezone('US/Eastern')

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape(self, chamber, session):
        if chamber != "other":
            return
        url = "http://www.leg.state.vt.us/HighlightsMain.cfm"
        page = self.lxmlize(url)
        ps = page.xpath(
            "//p[@class='HighlightsNote' or @class='HighlightsDate']")
        events = {}
        event_set = []
        for p in ps:
            if p.attrib['class'] == "HighlightsNote":
                event_set.append(p)
            else:
                date_time = p.text[len("Posted "):]
                events[date_time] = event_set
                event_set = []
        for date in events:
            date_time = dt.datetime.strptime(date, "%m/%d/%Y")
            for event in events[date]:
                descr = event.text_content()
                e = Event(session, date_time, "other", descr,
                          location="state house")
                e.add_source(url)
                self.save_event(e)
