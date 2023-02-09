import datetime
import json
import lxml
import re

import pytz

from openstates.scrape import Scraper, Event
from utils.events import match_coordinates
from openstates.exceptions import EmptyScrape

import datetime as dt
from dateutil.relativedelta import relativedelta
import dateutil.parser
import cloudscraper


class OHEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    base_url = "https://www.legislature.ohio.gov/schedules/"

    scraper = cloudscraper.create_scraper()

    def scrape(self, start=None, end=None):
        if start is None:
            start = dt.datetime.today()
        else:
            start = dateutil.parser.parse(start)

        if end is None:
            end = start + relativedelta(months=+3)
        else:
            end = dateutil.parser.parse(end)

        start = start.strftime("%Y-%m-%d")
        end = end.strftime("%Y-%m-%d")

        url = f"{self.base_url}calendar-data?start={start}&end={end}"
        try:
            data = json.loads(self.scraper.get(url).content)
        except Exception:
            raise EmptyScrape

        event_count = 0
        for item in data:
            name = item["title"].strip()
            status = "tentative"
            if "canceled" in name.lower():
                status = "cancelled"

            if "house session" in name.lower() or "senate session" in name.lower():
                continue

            if "url" not in item:
                self.warning(
                    f"No url or data provided for {item['title']} on {item['start']}, skipping."
                )
                continue

            url = f"{self.base_url}{item['url']}"

            when = dateutil.parser.parse(item["start"])
            when = self._tz.localize(when)

            page = self.scraper.get(url).content
            page = lxml.html.fromstring(page)

            location = page.xpath(
                '//div[h2[contains(text(), "Location")]]/p[3]/text()'
            )[0].strip()
            agenda_url = page.xpath(
                '//a[contains(@class,"link-button") and contains(text(),"Agenda")]/@href'
            )[0]

            if re.match(r"Room \d+", location, flags=re.IGNORECASE):
                location = f"{location}, 1 Capitol Square, Columbus, OH 43215"

            event = Event(
                name=name, start_date=when, location_name=location, status=status
            )

            match_coordinates(event, {"1 Capitol Square": (39.96019, -82.99946)})

            com_name = name.replace("Meeting", "").replace("CANCELED", "").strip()
            event.add_participant(com_name, type="committee", note="host")
            event.add_document("Agenda", agenda_url, media_type="application/pdf")
            event.add_source(url)
            event_count += 1
            yield event
        if event_count < 1:
            raise EmptyScrape
