import datetime
import json
import lxml

import pytz

from openstates.scrape import Scraper, Event

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
        data = json.loads(self.scraper.get(url).content)

        for item in data:
            name = item["title"].strip()
            if "canceled" in name.lower():
                continue

            if "house session" in name.lower() or "senate session" in name.lower():
                continue

            url = f"{self.base_url}{item['url']}"

            when = dateutil.parser.parse(item["start"])
            when = self._tz.localize(when)

            page = self.scraper.get(url).content
            page = lxml.html.fromstring(page)

            location = page.xpath(
                '//div[contains(@class,"eventModule") and h3[contains(text(), "Location")]]/text()'
            )[0].strip()
            agenda_url = page.xpath(
                '//a[contains(@class,"linkButton") and contains(text(),"Agenda")]/@href'
            )[0]

            event = Event(
                name=name,
                start_date=when,
                location_name=location,
            )

            event.add_participant(name, type="committee", note="host")
            event.add_document("Agenda", agenda_url, media_type="application/pdf")
            event.add_source(url)

            yield event
