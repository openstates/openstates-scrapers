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
    api_base_url = "https://search-prod.lis.state.oh.us/"
    session_id = ""

    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
    }

    def scrape(self, start=None, end=None):
        # pull the newest session id from __init__.py
        self.session_id = self.jurisdiction.legislative_sessions[-1]["identifier"]

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
            self.info(f"Fetching {url}")
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

            if re.match(r"^.*\shearing room", location, flags=re.IGNORECASE):
                location = f"{location}, 1 Capitol Square, Columbus, OH 43215"

            event = Event(
                name=name, start_date=when, location_name=location, status=status
            )

            match_coordinates(event, {"1 Capitol Square": (39.96019, -82.99946)})

            com_name = name.replace("Meeting", "").replace("CANCELED", "").strip()
            event.add_participant(com_name, type="committee", note="host")
            event.add_document("Agenda", agenda_url, media_type="application/pdf")
            event.add_source(url)

            # API has more data on agenda and bills, ex:
            # https://search-prod.lis.state.oh.us/solarapi/v1/general_assembly_135/notices/cmte_s_health_1/2023-03-01

            com_id = re.search(r"\/([a-z_]+\d)", item["url"], flags=re.IGNORECASE)
            if com_id:
                com_id = com_id.group(1)
                hearing_date = when.strftime("%Y-%m-%d")
                api_url = f"{self.api_base_url}/solarapi/v1/general_assembly_{self.session_id}/notices/{com_id}/{hearing_date}?format=json"
                self.info(f"Fetching {api_url}")
                api_data = json.loads(self.scraper.get(api_url).content)
                for row in api_data["agenda"]:
                    item_text = f"{row['headline']} - {row['proposed_sponsor']}"
                    agenda_item = event.add_agenda_item(item_text)
                    if "billno" in row:
                        agenda_item.add_bill(row["billno"])

                # Note: there's an api element called 'testimonies' that appears to just be
                # witness registration forms from the bill sponsors, so we're skipping those.

            event_count += 1
            yield event
        if event_count < 1:
            raise EmptyScrape
