import csv
import datetime
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html


class CTEventScraper(EventScraper):
    state = 'ct'

    _tz = pytz.timezone('US/Eastern')

    def __init__(self, *args, **kwargs):
        super(CTEventScraper, self).__init__(*args, **kwargs)

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)

        if chamber != 'other':
            # All CT committees are joint
            return

        for (code, name) in self.get_comm_codes():
            self.scrape_committee_events(session, code, name)

    def scrape_committee_events(self, session, code, name):
        url = ("http://www.cga.ct.gov/asp/menu/"
               "CGACommCal.asp?comm_code=%s" % code)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            cal_table = page.xpath(
                "//table[contains(@summary, 'Calendar')]")[0]

            date_str = None
            for row in cal_table.xpath("tr[2]//tr"):
                col1 = row.xpath("string(td[1])").strip()
                col2 = row.xpath("string(td[2])").strip()

                if not col1:
                    if col2 == "No Meetings Scheduled":
                        return
                    # If col1 is empty then this is a date header
                    date_str = col2
                else:
                    # Otherwise, this is a committee event row
                    when = date_str + " " + col1
                    when = datetime.datetime.strptime(
                        when, "%A, %B %d, %Y %I:%M %p")
                    when = self._tz.localize(when)

                    location = row.xpath("string(td[3])").strip()
                    guid = row.xpath("td/a")[0].attrib['href']

                    event = Event(session, when, 'committee meeting',
                                  col2, location, _guid=guid)
                    event.add_source(url)
                    event.add_participant('committee', name,
                                          chamber='joint')

                    self.save_event(event)

    def get_comm_codes(self):
        with self.urlopen("ftp://ftp.cga.ct.gov/pub/data/committee.csv") as page:
            page = csv.DictReader(StringIO.StringIO(page))

            return [(row['comm_code'].strip(),
                     row['comm_name'].strip())
                    for row in page]
