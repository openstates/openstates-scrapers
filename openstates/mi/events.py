import datetime as dt

from billy.scrape.events import Event, EventScraper

import lxml.html
import pytz

mi_events = "http://legislature.mi.gov/doc.aspx?CommitteeMeetings"

class MIEventScraper(EventScraper):
    state = 'mi'

    _tz = pytz.timezone('US/Eastern')

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape_event_page(self, url, chamber, session):
        page = self.lxmlize(url)
        trs = page.xpath("//table[@id='frg_committeemeeting_MeetingTable']/tr")
        metainf = {}
        for tr in trs:
            tds = tr.xpath(".//td")
            if len(tds) <= 1:
                continue
            key = tds[0].text_content().strip()
            val = tds[1]
            metainf[key] = {
                "txt": val.text_content().strip(),
                "obj": val
            }

        if metainf == {}:
            return

        # Wednesday, 5/16/2012 3:00 pm
        datetime = "%s %s" % (
            metainf['Date']['txt'],
            metainf['Time']['txt']
        )
        if "Cancelled" in datetime:
            return

        datetime = dt.datetime.strptime(datetime, "%A, %m/%d/%Y %I:%M %p")
        where = metainf['Location']['txt']
        title = metainf['Committee']['txt']  # XXX: Find a better title


        event = Event(session, datetime, 'committee:meeting',
                      title, location=where)
        event.add_source(url)
        event.add_source(mi_events)

        event.add_participant('host', metainf['Committee']['txt'],
                              chamber=chamber)

        agenda = metainf['Agenda']['obj']
        related_bills = agenda.xpath("//a[contains(@href, 'getObject')]")
        for bill in related_bills:
            event.add_related_bill(
                bill.text_content(),
                description=agenda.text_content(),
                type='consideration'
            )

        self.save_event(event)

    def scrape(self, chamber, session):
        page = self.lxmlize(mi_events)
        xpaths = {
            "lower": "//span[@id='frg_committeemeetings_HouseMeetingsList']",
            "upper": "//span[@id='frg_committeemeetings_SenateMeetingsList']",
            "other": "//span[@is='frg_committeemeetings_JointMeetingsList']"
        }
        span = page.xpath(xpaths[chamber])
        if len(span) > 0:
            span = span[0]
        else:
            return
        events = span.xpath("//a[contains(@href, 'committeemeeting')]")
        for event in events:
            self.scrape_event_page(event.attrib['href'], chamber, session)
