import re
import datetime as dt

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper
from openstates.utils import LXMLMixin

import pytz
import lxml.html

urls = "http://www.malegislature.gov/Events/%s"
pages = {
    "upper" : [ urls % "SenateSessions" ],
    "lower" : [ urls % "HouseSessions" ],
    "other" : [ urls % "JointSessions",
                urls % "Hearings", urls % "SpecialEvents" ]
}

class MAEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'ma'

    _tz = pytz.timezone('US/Eastern')

    def add_agenda(self, event, url):
        event.add_source(url)
        page = self.lxmlize(url)
        description = page.xpath("//div[@id='eventData']/p")
        if len(description) > 0:
            description = description[0].text_content().strip()
            if description != "":
                event['description'] = description

        # Let's (hillariously) add "Chair"(s) to the event.
        people = page.xpath("//a[contains(@href, 'People')]")
        for person in people:
            if "Facilitator" in person.text_content():
                kruft, chair = person.text_content().split(":", 1)
                kruft = kruft.strip()
                chair = chair.strip()
                chamber = 'other'
                if "senate" in kruft:
                    chamber = 'upper'
                elif "house" in kruft:
                    chamber = 'lower'

                event.add_participant('chair', chair, 'legislator',
                                      position_name=kruft,
                                      chamber=chamber)

        trs = page.xpath("//tbody/tr")
        for tr in trs:
            # Alright. Let's snag some stuff.
            cells = {
                "num" : "agendaItemNum",
                "bill_id": "agendaBillNum",
                "title": "agendaBillTitle",
                "spons": "agendaBillSponsor"
            }
            metainf = {}
            for cell in cells:
                metainf[cell] = tr.xpath(".//td[@class='" + cells[cell] + "']")
            if metainf['bill_id'] == []:
                return
            kwargs = { "type" : "consideration" }
            # Alright. We can assume we have at least the bill ID.
            bill_id = metainf['bill_id'][0].text_content().strip()
            if cells['title'] != []:
                kwargs['description'] = metainf['title'][0].text_content(
                    ).strip()
            # XXX: Add sponsors.
            event.add_related_bill(bill_id, **kwargs)


    def parse_row(self, row, session, chamber):
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
        cells = {
            "event": "eventCell",
            "status": "statusCell",
            "location": "locationCell",
            "transcript": "transcriptCell",
            "video": "videoCell"
        }
        metainf = {}
        for thing in cells:
            mi = row.xpath("./td[@class='" + cells[thing] + "']")
            if mi == []:
                continue
            metainf[thing] = mi[0]

        if metainf['location'].xpath("./*") == []:
            metainf['location'] = self.last_location
        else:
            self.last_location = metainf['location']

        if "Session" in metainf['event'].text_content().strip():
            return  # Nada.

        loc_url = metainf['location'].xpath(".//a")
        loc_url = loc_url[0].attrib['href']
        event = Event(session,
                      when,
                      'committee:meeting',
                      metainf['event'].text_content().strip(),
                      chamber=chamber,
                      location=metainf['location'].text_content().strip(),
                      location_url=loc_url)
        event.add_participant("host", metainf['event'].text_content().strip(),
                              'committee', chamber=chamber)
        self.add_agenda(event, metainf['event'].xpath(".//a")[0].attrib['href'])
        return event

    def scrape(self, chamber, session):
        scrape_list = pages[chamber]
        self.year = dt.datetime.now().year
        for site in scrape_list:
            page = self.lxmlize(site)
            rows = page.xpath("//tbody[not(contains(@id, 'noDates'))]/tr[contains(@class, 'dataRow')]")
            for row in rows:
                event = self.parse_row(row, session, chamber)
                if event:
                    event.add_source(site)
                    self.save_event(event)
