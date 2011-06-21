import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html
import feedparser


class TXEventScraper(EventScraper):
    state = 'tx'

    _tz = pytz.timezone('US/Central')

    def scrape(self, chamber, session):
        if not session.startswith('82'):
            raise NoDataForPeriod(session)

        self.scrape_committee_upcoming(session, chamber)

    def scrape_committee_upcoming(self, session, chamber):
        chamber_name = {'upper': 'senate',
                        'lower': 'house',
                        'other': 'joint'}[chamber]
        url = ("http://www.capitol.state.tx.us/MyTLO/RSS/RSS.aspx?"
               "Type=upcomingmeetings%s" % chamber_name)

        with self.urlopen(url) as page:
            feed = feedparser.parse(page)

            for entry in feed['entries']:
                try:
                    title, date = entry['title'].split(' - ')
                except ValueError:
                    continue

                desc = entry['description'].strip()
                match = re.match(
                    r'Time: (\d+:\d+ (A|P)M)((\s+\(.*\))|( or .*))?, Location:',
                    desc)
                if match:
                    dt = "%s %s" % (date, match.group(1))
                    when = datetime.datetime.strptime(dt,
                                                  '%m/%d/%Y %I:%M %p')
                    when = self._tz.localize(when)
                    all_day = False

                    notes = match.group(3)
                    if notes:
                        notes = "Time: " + notes.strip()
                    else:
                        notes = ""
                else:
                    match = re.match(r'Time: (.*), Location:', desc)
                    if match:
                        when = datetime.datetime.strptime(date,
                                                          '%m/%d/%Y').date()
                        all_day = True
                        notes = "Time: " + match.group(1).strip()

                if '(Canceled)' in notes:
                    status = 'canceled'
                else:
                    status = 'confirmed'

                location = entry['description'].split('Location: ')[1]

                description = 'Committee Meeting\n'
                description += entry['title'] + '\n'
                description += entry['description']

                event = Event(session, when, 'committee:meeting',
                              description,
                              location=location,
                              status=status,
                              all_day=all_day,
                              link=entry['link'])
                event.add_participant('committee', title, chamber=chamber)

                event['_guid'] = entry['guid']

                with self.urlopen(entry['link']) as page:
                    page = lxml.html.fromstring(page)
                    text = page.xpath("string(//body)")
                    text = re.sub(r'(\r\n\s*)+', '\n', text).strip()
                    text = text.encode('ascii', 'ignore')
                    notes += "\n\n" + text

                event['notes'] = notes.strip()

                event['link'] = entry['link']

                event.add_source(url)

                self.save_event(event)
