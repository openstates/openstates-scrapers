import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import pytz
import feedparser


class TXEventScraper(EventScraper):
    state = 'tx'

    _tz = pytz.timezone('US/Central')

    def scrape(self, chamber, session):
        if session != '82':
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
                    notes = notes.strip() if notes else None

                    if notes == '(Canceled)':
                        status = 'canceled'
                    else:
                        status = 'confirmed'
                else:
                    match = re.match(r'Time: (.*), Location:', desc)
                    if match:
                        when = datetime.datetime.strptime(date,
                                                          '%m/%d/%Y').date()
                        all_day = True
                        notes = match.group(1).strip()
                        status = 'confirmed'

                location = entry['description'].split('Location: ')[1]

                description = 'Committee Meeting\n'
                description += entry['title'] + '\n'
                description += entry['description']

                event = Event(session, when, 'committee:meeting',
                              description,
                              location=location,
                              status=status,
                              notes=notes,
                              all_day=all_day)
                event.add_participant('committee', title)

                event['_guid'] = entry['guid']
                event['link'] = entry['link']

                event.add_source(url)

                self.save_event(event)
