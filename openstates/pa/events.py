import re
import datetime
import urlparse

from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html


class PAEventScraper(EventScraper):
    state = 'pa'

    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        if chamber == 'upper':
            url = "http://www.legis.state.pa.us/WU01/LI/CO/SM/COSM.HTM"
        elif chamber == 'lower':
            url = "http://www.legis.state.pa.us/WU01/LI/CO/HM/COHM.HTM"
        else:
            return

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for date_td in page.xpath("//td[@valign='middle']"):
                date = date_td.text_content().strip()

                datetime.datetime.strptime(
                    date, "%A, %B %d, %Y").date()

                next_tr = date_td.getparent().getnext()
                while next_tr is not None:
                    if next_tr.xpath("td[@valign='middle']"):
                        break

                    time = next_tr.xpath("string(td[1])").strip()
                    dt = "%s %s" % (date, time)

                    try:
                        dt = datetime.datetime.strptime(
                            dt, "%A, %B %d, %Y %I:%M %p")
                        dt = self._tz.localize(dt)
                    except ValueError:
                        break

                    desc = next_tr.xpath("string(td[2])").strip()
                    desc_el = next_tr.xpath("td[2]")[0]
                    desc = re.sub(r'\s+', ' ', desc)

                    related_bills = desc_el.xpath(
                        ".//a[contains(@href, 'billinfo')]")
                    bills = []
                    urls = [x.attrib['href'] for x in related_bills]

                    for u in urls:
                        o = urlparse.urlparse(u)
                        qs = urlparse.parse_qs(o.query)
                        bills.append({
                            "bill_id": "%sB %s" % ( qs['body'][0], qs['bn'][0] ),
                            "bill_num": qs['bn'][0],
                            "bill_chamber": qs['body'][0],
                            "session": qs['syear'][0],
                            "descr": desc
                        })
                    print bills

                    location = next_tr.xpath("string(td[3])").strip()
                    location = re.sub(r'\s+', ' ', location)

                    event = Event(session, dt, 'committee:meeting',
                                  desc, location)
                    event.add_source(url)
                    for bill in bills:
                        event.add_related_bill(
                            bill['bill_id'],
                            description=bill['descr'],
                            type='consideration'
                        )
                    self.save_event(event)
                    next_tr = next_tr.getnext()
