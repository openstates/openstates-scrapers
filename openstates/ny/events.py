import re
import datetime as dt

from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html

url = "http://assembly.state.ny.us/leg/?sh=hear"

class NYEventScraper(EventScraper):
    _tz = pytz.timezone('US/Eastern')
    state = 'ny'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def parse_page(self, url, session):
        page = self.lxmlize(url)
        tables = page.xpath("//table[@class='pubhrgtbl']")
        date = None
        ctty = None
        chamber = 'other'
        for table in tables:
            metainf = {}
            rows = table.xpath(".//tr")
            for row in rows:
                tds = row.xpath("./*")
                if len(tds) < 2:
                    continue
                key, value = tds
                if key.tag == 'th':
                    date = key.text_content()
                    date = re.sub("\s+", " ", date)
                    date = re.sub(".*POSTPONED NEW DATE", "", date).strip()
                    ctty = value.xpath(".//strong")[0]
                    ctty = ctty.text_content()

                    chamber = 'other'
                    if "senate" in ctty.lower():
                        chamber = 'upper'
                    if "house" in ctty.lower():
                        chamber = 'lower'
                    if "joint" in ctty.lower():
                        chamber = 'joint'
                elif key.tag == 'td':
                    key = key.text_content().strip()
                    value = value.text_content().strip()
                    value = value.replace(u'\x96', '-')
                    value = re.sub("\s+", " ", value)
                    metainf[key] = value


            time = metainf['Time:']
            repl = {
                "A.M." : "AM",
                "P.M." : "PM"
            }
            for r in repl:
                time = time.replace(r, repl[r])

            time = re.sub("-.*", "", time)
            time = time.strip()

            year = dt.datetime.now().year

            date = "%s %s %s" % (
                date,
                year,
                time
            )
            datetime = dt.datetime.strptime(date, "%B %m %Y %I:%M %p")
            event = Event(session, datetime, 'committee:meeting',
                          metainf['Public Hearing:'],
                          location=metainf['Place:'],
                          contact=metainf['Contact:'],
                          media_contact=metainf['Media Contact:'])
            event.add_source(url)
            event.add_participant('host',
                                  ctty,
                                  chamber=chamber)
            self.save_event(event)

    def scrape(self, chamber, session):
        if chamber == 'other':
            self.parse_page(url, session)
