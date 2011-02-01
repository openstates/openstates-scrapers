import os
import re
import datetime

from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html


class PAEventScraper(EventScraper):
    state = 'pa'

    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        if chamber == 'upper':
            url = "http://www.legis.state.pa.us/WU01/LI/CO/SM/COSM.HTM"
        else:
            url = "http://www.legis.state.pa.us/WU01/LI/CO/HM/COHM.HTM"

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for date_td in page.xpath("//td[@valign='middle']"):
                date = date_td.text.strip()

                datetime.datetime.strptime(
                    date_td.text.strip(), "%A, %B %d, %Y").date()

                next_tr = date_td.getparent().getnext()
                while next_tr is not None:
                    if next_tr.xpath("td[@valign='middle']"):
                        break

                    time = next_tr.xpath("string(td[1])").strip()
                    dt = "%s %s" % (date, time)

                    try:
                        dt = datetime.datetime.strptime(
                            dt, "%A, %B %d, %Y %H:%M %p")
                        dt = self._tz.localize(dt)
                    except ValueError:
                        break

                    desc = next_tr.xpath("string(td[2])").strip()
                    desc = re.sub(r'\s+', ' ', desc)

                    location = next_tr.xpath("string(td[3])").strip()
                    location = re.sub(r'\s+', ' ', location)

                    event = Event(session, dt, 'committee:meeting',
                                  desc, location)
                    event.add_source(url)
                    self.save_event(event)

                    next_tr = next_tr.getnext()
