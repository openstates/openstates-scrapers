import pytz
import dateutil.parser

import re
from utils import LXMLMixin
from openstates.scrape import Scraper, Event

from openstates.exceptions import EmptyScrape
from utils.events import match_coordinates

calurl = "https://committeeschedule.legis.wisconsin.gov/?StartDate=2025-01-30&CommitteeID=-1&CommItemVisibleName=-1&TopicID=-1&ViewType=listBiennium&ReloadCache=True"


# TODO: We may be able to scrape additional documents and minutes
# from the committee page at com_url, but the page structure is a mess.
class WIEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Central")

    def scrape(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
        }

        html = self.get(calurl, headers=headers).text
        # events here are inline in the html as JS variables
        event_regex = r"({[\n\s]*title(.*?)}),\/\/end event object"
        event_rows = re.findall(event_regex, html, flags=re.MULTILINE | re.DOTALL)

        if len(event_rows) == 0:
            raise EmptyScrape

        events = set()
        for row in event_rows:
            row = row[0]
            title = self.extract_field(row, "title")
            start = self.extract_field(row, "start")

            start = dateutil.parser.parse(start)
            start = self._tz.localize(start)

            desc = self.extract_field(row, "description")
            url = self.extract_field(row, "url")
            location = self.extract_field(row, "location")
            location = f"{location}, 2 E Main St, Madison, WI 53703"

            com_url = self.extract_field(row, "commLink")

            agenda_url = self.extract_field(row, "mtgNoticeLink")
            items = self.extract_field(row, "eItems")
            event_name = f"{title}#{location}#{start}"
            if event_name in events:
                self.warning(f"Duplicate event {event_name}")
                continue
            events.add(event_name)
            event = Event(
                name=title, location_name=location, start_date=start, description=desc
            )
            event.dedupe_key = event_name
            event.add_source(url)
            event.add_source(com_url)

            # rename from "Committee Name (Senate)" to "Senate Committee Name"
            chamber_regex = r"(.*)\((Senate|Assembly|Joint)\)"
            if re.match(chamber_regex, title):
                committee = re.sub(chamber_regex, r"\2 \1", title).strip()
                event.add_committee(committee)

            if agenda_url:
                event.add_document("Agenda", agenda_url, media_type="application/pdf")

            if items != "(None)":
                items = items.split(";")
                for item in items:
                    item = item.replace("&amp", "").strip()
                    if not item:
                        self.warning(f"Empty agenda item ({item}) for {event}")
                        continue
                    agenda_item = event.add_agenda_item(item)
                    bill_regex = r"[SAJRPB]+\d+"
                    for bill_match in re.findall(bill_regex, item):
                        agenda_item.add_bill(bill_match)

            match_coordinates(event, {"2 E Main St": (43.07499, -89.38415)})

            yield event

    def extract_field(self, row: str, field: str):
        try:
            return re.findall(
                rf"{field}:\s+'(.*?)'", row, flags=re.MULTILINE | re.DOTALL
            )[0]
        except IndexError:
            return None
