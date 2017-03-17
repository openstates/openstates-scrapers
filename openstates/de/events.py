import datetime as dt

from openstates.utils import LXMLMixin
from pupa.scrape import Event, Scraper

import pytz
import lxml.html

chamber_urls = {
    "other": [],
    "lower": ["http://legis.delaware.gov/LIS/lis146.nsf/House+Meeting+Notice/?openview&count=2000"],
    "upper": ["http://legis.delaware.gov/LIS/lis146.nsf/Senate+Meeting+Notice/?openview&count=2000"]
}
chambers = {
    "Senate": "upper",
    "House": "lower",
    "Joint": "joint"
}


class DEEventScraper(Scraper, LXMLMixin):
    jurisdiction = 'de'

    _tz = pytz.timezone('US/Eastern')

    def scrape_meeting_notice(self, chamber, url):
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
        metainf[date_time_lbl] = dt.datetime.strptime(metainf[date_time_lbl], fmt)

        event = Event(timezone=self._tz.zone,
                      location_name=metainf['Room'],
                      start_time=self._tz.localize(metainf[date_time_lbl]),
                      name=metainf['Committee']
                      )

        event.add_participant(metainf['Committee'], type='committee', note='host')
        event.add_source(url)

        # TODO what is alternative of add_related_bill ?
        """
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
        """
        yield event

    def scrape(self, chamber=None):
        chambers_ = [chamber] if chamber is not None else ['upper', 'lower', 'other']
        # self.log(chamber)
        for chamber in chambers_:
            urls = chamber_urls[chamber]
            for url in urls:
                page = self.lxmlize(url)
                events = page.xpath("//a[contains(@href, 'OpenDocument')]")
                for event in events:
                    yield from self.scrape_meeting_notice(chamber, event.attrib['href'])
