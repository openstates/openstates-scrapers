import datetime as dt

from openstates.utils import LXMLMixin
from billy.scrape.events import Event, EventScraper

import pytz
import lxml.html

chamber_urls = {
    "other" : [],
    "lower" : [ "http://legis.delaware.gov/LIS/lis146.nsf/House+Meeting+Notice/?openview&count=2000" ],
    "upper" : [ "http://legis.delaware.gov/LIS/lis146.nsf/Senate+Meeting+Notice/?openview&count=2000" ]
}
chambers = {
    "Senate" : "upper",
    "House"  : "lower",
    "Joint"  : "joint"
}

class DEEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'de'

    _tz = pytz.timezone('US/Eastern')

    def scrape_meeting_notice(self, chamber, session, url):
        page = self.lxmlize(url)
        bits = page.xpath("//td[@width='96%']/table/tr")
        metainf = {}
        for bit in bits:
            info = bit.xpath(".//td")
            key = info[0].text_content().strip()
            val = info[1].text_content().strip()
            if key[-1:] == ":":
                key = key[:-1]
            metainf[key] = val
        date_time_lbl = "Date/Time"
        # 04/25/2012 03:00:00 PM
        fmt = "%m/%d/%Y %I:%M:%S %p"
        metainf[date_time_lbl] = dt.datetime.strptime(metainf[date_time_lbl],
                                                     fmt)
        event = Event(session,
                      metainf[date_time_lbl],
                      "committee:meeting",
                      "Committee Meeting",
                      chamber=chambers[metainf['Chamber']],
                      location=metainf['Room'],
                      chairman=metainf['Chairman'])
        event.add_participant("host", metainf['Committee'], 'committee',
                              chamber=chambers[metainf['Chamber']])
        event.add_source(url)

        agenda = page.xpath("//td[@width='96%']//font[@face='Arial']")
        agenda = [ a.text_content().strip() for a in agenda ]
        if "" in agenda:
            agenda.remove("")
        for item in agenda:
            string = item.split()
            string = string[:2]
            fChar = string[0][0]
            watch = [ "H", "S" ]
            if fChar in watch:
                try:
                    bNo = int(string[1])
                except ValueError:
                    continue
                except IndexError:
                    continue
                bill_id = "%s %s" % ( string[0], string[1] )
                event.add_related_bill(
                    bill_id,
                    description=item,
                    type="consideration"
                )

        self.save_event(event)

    def scrape(self, chamber, session):
        self.log(chamber)
        urls = chamber_urls[chamber]
        for url in urls:
            page = self.lxmlize(url)
            events = page.xpath("//a[contains(@href, 'OpenDocument')]")
            for event in events:
                self.scrape_meeting_notice(chamber, session,
                                           event.attrib['href'])
