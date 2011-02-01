import os
import re
import datetime

from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html


class UTEventScraper(EventScraper):
    state = 'ut'

    _tz = pytz.timezone('US/Mountain')

    def scrape(self, chamber, session):
        for month in xrange(1, 13):
            self.scrape_month(chamber, session, month)

    def scrape_month(self, chamber, session, month):
        url = ("http://le.utah.gov/asp/interim/"
               "Cal.asp?year=2011&month=%d" % month)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            day = 1
            for td in page.xpath("//td[@bgcolor='#FFFFCC']"):
                for font in td.xpath(
                    "//font[contains(text(), 'Floor Time')]"):

                    match = re.search(
                        "(\d+:\d+ [AP]M)-(\d+:\d+ [AP]M) (House|Senate) "
                        "Chamber", font.text)

                    if not match:
                        continue

                    chamber_name = match.group(3)
                    ev_chamber = {'Senate': 'upper',
                               'House': 'lower'}[chamber_name]
                    if ev_chamber != chamber:
                        continue

                    start = datetime.datetime.strptime(
                        "%d %d 2011 %s" % (month, day, match.group(1)),
                        "%m %d %Y %H:%M %p")
                    end = datetime.datetime.strptime(
                        "%d %d 2011 %s" % (month, day, match.group(2)),
                        "%m %d %Y %H:%M %p")

                    event = Event(session, start, 'floor_time',
                                  '%s Floor Time' % chamber_name,
                                  '%s Chamber' % chamber_name,
                                  end=end)
                    event.add_source(url)
                    self.save_event(event)

                for link in td.xpath("//a[contains(@href, 'Commit.asp')]"):
                    comm = link.xpath("string()").strip()

                    if chamber == 'upper' and not comm.startswith('Senate'):
                        continue
                    elif chamber == 'lower' and not comm.startswith('House'):
                        continue

                    preceding_link = link.xpath("preceding-sibling::a[1]")[0]
                    if (preceding_link.getnext().xpath("string()") ==
                        ' CANCELED'):

                        continue

                    time_loc = preceding_link.xpath("string()")
                    time, location = re.match(
                        r"(\d+:\d+ [AP]M)(.*)$", time_loc).groups()

                    when = datetime.datetime.strptime(
                        "%d %d 2011 %s" % (month, day, time),
                        "%m %d %Y %H:%M %p")

                    event = Event(session, when, 'committee:meeting',
                                  'Committee Meeting\n%s' % comm,
                                  location=location,
                                  _guid=link.attrib['href'])
                    event.add_source(url)
                    self.save_event(event)

                day += 1
