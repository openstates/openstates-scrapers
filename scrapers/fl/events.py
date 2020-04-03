import pytz
import datetime
import feedparser
from openstates.scrape import Scraper, Event


class FlEventScraper(Scraper):
    tz = pytz.timezone("US/Eastern")

    def scrape(self):
        yield from self.scrape_upper_events()

    def scrape_upper_events(self):
        url = "https://www.flsenate.gov/Tracker/RSS/DailyCalendar"
        page = self.get(url).text
        feed = feedparser.parse(page)
        for entry in feed["entries"]:
            # The feed breaks the RSS standard by making the pubdate the
            # actual event's date, not the RSS item publish date
            when = datetime.datetime(*entry["published_parsed"][:6])
            when = pytz.utc.localize(when)

            desc = entry["summary"].split(" - ")[0]
            location = entry["summary"].split(" - ")[1]

            event = Event(
                name=desc, start_date=when, description=desc, location_name=location
            )

            event.add_source(entry["link"])
            yield event
