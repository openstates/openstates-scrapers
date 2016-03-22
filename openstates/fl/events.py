import re
import datetime

from billy.scrape.events import EventScraper, Event

import feedparser


class FLEventScraper(EventScraper):
    jurisdiction = 'fl'

    def scrape(self, chamber, session):
        self.scrape_upper_events(session)

    def scrape_upper_events(self, session):
        url = "https://www.flsenate.gov/Tracker/RSS/DailyCalendar"
        page = self.get(url).text
        feed = feedparser.parse(page)

        for entry in feed['entries']:            
            #The feed breaks the RSS standard by making the pubdate the actual event's date, not the RSS item publish date
            when = datetime.datetime(*entry['published_parsed'][:6])

            desc = entry['summary'].split(' - ')[0]
            location = entry['summary'].split(' - ')[1]

            event = Event(session, when, 'committee:meeting',
                              desc, location)
            event.add_source(entry['link'])

            self.save_event(event)
