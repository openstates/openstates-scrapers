import datetime as dt
import re

from openstates.utils import LXMLMixin
from billy.scrape.events import Event, EventScraper

import lxml.html
import pytz

urls = {
    "upper": "http://www.ilga.gov/senate/schedules/weeklyhearings.asp",
    "lower": "http://www.ilga.gov/house/schedules/weeklyhearings.asp"
}


class ILEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'il'
    _tz = pytz.timezone('US/Eastern')

    def scrape_page(self, url, session, chamber):
        page = self.lxmlize(url)

        ctty_name = page.xpath("//span[@class='heading']")[0].text_content()

        tables = page.xpath("//table[@cellpadding='3']")
        info = tables[0]
        rows = info.xpath(".//tr")
        metainf = {}
        for row in rows:
            tds = row.xpath(".//td")
            key = tds[0].text_content().strip()
            value = tds[1].text_content().strip()
            metainf[key] = value

        where = metainf['Location:']
        description = ctty_name

        datetime = metainf['Scheduled Date:']
        datetime = re.sub("\s+", " ", datetime)
        repl = {
            "AM": " AM",
            "PM": " PM"  # Space shim.
        }
        for r in repl:
            datetime = datetime.replace(r, repl[r])
        datetime = dt.datetime.strptime(datetime, "%b %d, %Y %I:%M %p")

        event = Event(session, datetime, 'committee:meeting',
                      description, location=where)
        event.add_source(url)

        if ctty_name.startswith('Hearing Notice For'):
            ctty_name.replace('Hearing Notice For', '')
        event.add_participant('host', ctty_name, 'committee', chamber=chamber)

        bills = tables[1]
        for bill in bills.xpath(".//tr")[1:]:
            tds = bill.xpath(".//td")
            if len(tds) < 4:
                continue
            # First, let's get the bill ID:
            bill_id = tds[0].text_content()
            event.add_related_bill(bill_id,
                                   description=description,
                                   type='consideration')

        self.save_event(event)

    def scrape(self, chamber, session):
        try:
            url = urls[chamber]
        except KeyError:
            return  # Not for us.
        page = self.lxmlize(url)
        tables = page.xpath("//table[@width='550']")
        for table in tables:
            meetings = table.xpath(".//a")
            for meeting in meetings:
                self.scrape_page(meeting.attrib['href'],
                                 session, chamber)
