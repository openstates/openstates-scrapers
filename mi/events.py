from openstates.utils import LXMLMixin
import datetime as dt
import re

from billy.scrape.events import Event, EventScraper

import lxml.html
import pytz

mi_events = "http://legislature.mi.gov/doc.aspx?CommitteeMeetings"

class MIEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'mi'

    _tz = pytz.timezone('US/Eastern')

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
            metainf['Time']['txt'].replace(".","")
        )
        if "Cancelled" in datetime:
            return

        translate = {
            "noon": " PM",
            "a.m.": " AM",
            "am": " AM",  # This is due to a nasty line they had.
            "a.m": "AM" #another weird one

        }

        for t in translate:
            if t in datetime:
                datetime = datetime.replace(t, translate[t])

        datetime = re.sub("\s+", " ", datetime)

        for text_to_remove in [
                "or after committees are given leave",
                "or later immediately after committees are given leave",
                "or later after committees are given leave by the House to meet",
                "**Please note time**"
                ]:
            datetime = datetime.split(text_to_remove)[0].strip()

        datetime = datetime.replace('p.m.', 'pm')
        datetime = datetime.replace('Noon',"pm")
        datetime = dt.datetime.strptime(datetime, "%A, %m/%d/%Y %I:%M %p")
        where = metainf['Location']['txt']
        title = metainf['Committee']['txt']  # XXX: Find a better title

        if chamber == 'other':
            chamber = 'joint'

        event = Event(session, datetime, 'committee:meeting',
                      title, location=where)
        event.add_source(url)
        event.add_source(mi_events)

        chair_name = metainf['Chair']['txt'].strip()
        if chair_name:
            event.add_participant('chair', chair_name, 'legislator', chamber=chamber)
        else:
            self.warning("No chair found for event '{}'".format(title))

        event.add_participant('host', metainf['Committee']['txt'],
                              'committee',
                              chamber=chamber)

        agenda = metainf['Agenda']['obj']
        agendas = agenda.text_content().split("\r")

        related_bills = agenda.xpath("//a[contains(@href, 'getObject')]")
        for bill in related_bills:
            description = agenda
            for a in agendas:
                if bill.text_content() in a:
                    description = a

            event.add_related_bill(
                bill.text_content(),
                description=description,
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
        events = span.xpath(".//a[contains(@href, 'committeemeeting')]")
        for event in events:
            url = event.attrib['href']
            if 'doPostBack' in url:
                continue
            self.scrape_event_page(url, chamber, session)
