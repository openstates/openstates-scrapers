import datetime
import dateutil.parser
import json
import lxml.html
import pytz
import re
import requests

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

from utils.events import match_coordinates


class OKEventScraper(Scraper):
    _tz = pytz.timezone("CST6CDT")
    session = requests.Session()

    # usage:
    # poetry run os-update ne \
    # events --scrape start=2022-02-01 end=2022-03-02
    def scrape(self, start=None, end=None):

        if start is None:
            delta = datetime.timedelta(days=90)
            start = datetime.date.today() - delta
            start = start.isoformat()

            end = datetime.date.today() + delta
            end = end.isoformat()

        yield from self.scrape_page(start, end)

    def scrape_page(self, start, end, offset=0, limit=20):
        self.info(f"Fetching {start} - {end} offset {offset}")

        url = "https://www.okhouse.gov/api/events"

        post_data = {
            "start": f"{start}T00:00:00.000Z",
            "end": f"{end}T00:00:00.000Z",
            "offset": offset,
            "limit": limit,
        }

        headers = {"origin": "https://www.okhouse.gov", "user-agent": "openstates.org"}

        page = requests.post(
            url=url, data=json.dumps(post_data), headers=headers, allow_redirects=True
        ).content
        page = json.loads(page)

        if offset == 0 and len(page["events"]["data"]) == 0:
            raise EmptyScrape

        for row in page["events"]["data"]:
            meta = row["attributes"]

            status = "tentative"

            if meta["isCancelled"] is True:
                status = "cancelled"

            if meta["location"]:
                location = meta["location"]
                if re.match(r"^room [\w\d]+$", location, flags=re.I) or re.match(
                    r"senate room [\w\d]+$", location, flags=re.I
                ):
                    location = (
                        f"{location} 2300 N Lincoln Blvd, Oklahoma City, OK 73105"
                    )
            else:
                meta["location"] = "See agenda"

            when = dateutil.parser.parse(meta["startDatetime"])

            event = Event(
                name=meta["title"],
                location_name=location,
                start_date=when,
                classification="committee-meeting",
                status=status,
            )
            event.dedupe_key = f"ok-{meta['slug']}"
            event.add_source(f"https://www.okhouse.gov/events/{meta['slug']}")
            match_coordinates(event, {"2300 N Lincoln Blvd": (35.49293, -97.50311)})

            if meta["committee"]["data"]:
                event.add_committee(
                    meta["committee"]["data"]["attributes"]["name"], note="host"
                )

            for link in meta["links"]:
                event.add_document(
                    link["label"], link["route"], media_type="application/pdf"
                )

            for agenda in meta["agenda"]:
                agenda_text = lxml.html.fromstring(agenda["info"])
                agenda_text = " ".join(agenda_text.xpath("//text()"))
                item = event.add_agenda_item(agenda_text)

                if agenda["measure"]["data"]:
                    item.add_bill(agenda["measure"]["data"])
                    self.info(agenda["measure"])
                    self.error(
                        "Finally found an agenda with linked measure. Modify the code to handle it."
                    )

                # sometimes they put the bill number here instead
                if agenda["customId"]:
                    item.add_bill(agenda["customId"])

            yield event

        current_max = offset + limit
        if page["events"]["meta"]["pagination"]["total"] > current_max:
            yield from self.scrape_page(start, end, offset + limit, limit)
