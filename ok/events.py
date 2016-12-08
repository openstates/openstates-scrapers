import re
import datetime
import time

from billy.scrape.events import EventScraper, Event

import lxml.html


class OKEventScraper(EventScraper):
    jurisdiction = 'ok'

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_upper(session)

    def scrape_upper(self, session):
        url = "http://www.oksenate.gov/Committees/meetingnotices.htm"
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        text = page.text_content()
        _, text = text.split('MEETING NOTICES')
        re_date = r'[A-Z][a-z]+,\s+[A-Z][a-z]+ \d+, \d{4}'
        chunks = zip(re.finditer(re_date, text), re.split(re_date, text)[1:])

        for match, data in chunks:
            when = match.group()
            when = datetime.datetime.strptime(when, "%A, %B %d, %Y")

            lines = filter(None, [x.strip() for x in data.splitlines()])

            time_ = re.search(r'^\s*TIME:\s+(.+?)\s+\x96', data, re.M).group(1)
            time_ = time_.replace('a.m.', 'AM').replace('p.m.', 'PM')
            time_ = time.strptime(time_, '%I:%M %p')
            when += datetime.timedelta(hours=time_.tm_hour, minutes=time_.tm_min)

            title = lines[0]

            where = re.search(r'^\s*PLACE:\s+(.+)', data, re.M).group(1)
            where = where.strip()

            event = Event(session, when, 'committee:meeting', title,
                          location=where)
            event.add_source(url)

            self.save_event(event)
