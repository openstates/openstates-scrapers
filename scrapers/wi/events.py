import pytz
import dateutil.parser

import scrapelib
import re
from utils import LXMLMixin
from openstates.scrape import Scraper, Event

# from openstates.exceptions import EmptyScrape
from utils.events import match_coordinates

calurl = "http://committeeschedule.legis.wisconsin.gov/?filter=Upcoming&committeeID=-1"


class WIEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Central")

    def scrape_participants(self, href):
        try:
            page = self.lxmlize(href)
        except scrapelib.HTTPError:
            self.warning("Committee page not found for this event")
            return []

        legs = page.xpath("//a[contains(@href, '/Pages/leg-info.aspx')]/text()")
        role_map = {
            "participant": "participant",
            "Chair": "chair",
            "Co-Chair": "chair",
            "Vice-Chair": "participant",
        }
        ret = []
        for leg in legs:
            name = leg
            title = "participant"
            if "(" and ")" in leg:
                name, title = leg.split("(", 1)
                title = title.replace(")", " ").strip()
                name = name.strip()
            title = role_map[title]
            ret.append({"name": name, "title": title})
        return ret

    def scrape(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
        }

        html = self.get(calurl, headers=headers).text
        # {[\n\s]*title(.*?)},\/\/end event object
        print(html)

        # print(html)

        event_regex = r"({[\n\s]*title(.*?)}),\/\/end event object"
        event_rows = re.finditer(event_regex, html, flags=re.MULTILINE | re.DOTALL)

        for row in event_rows:
            row = row.groups(1)[0]
            title = self.extract_field(row, "title")
            start = self.extract_field(row, "start")

            start = dateutil.parser.parse(start)
            start = self._tz.localize(start)

            desc = self.extract_field(row, "description")
            url = self.extract_field(row, "url")
            location = self.extract_field(row, "location")
            location = f"{location}, 2 E Main St, Madison, WI 53703"

            # meeting_type = self.extract_field(row, "type")
            agenda_url = self.extract_field(row, "mtgNoticeLink")
            items = self.extract_field(row, "eItems")
            # chamber_class = self.extract_field(row, "classNames")

            event = Event(
                name=title, location_name=location, start_date=start, description=desc
            )
            event.add_source(url)

            # rename from "Committe Name (Senate)" to "Senate Committee Name"
            chamber_regex = r"(.*)\((Senate|Assembly|Joint)\)"
            if re.match(chamber_regex, title):
                committee = re.sub(chamber_regex, r"\2 \1", title).strip()
                event.add_committee(committee)

            if agenda_url:
                event.add_document("Agenda", agenda_url, media_type="application/pdf")

            if items != "(None)":
                items = items.split(";")
                print(items)
                for item in items:
                    item = item.replace("&amp", "").strip()
                    print(item)
                    agenda_item = event.add_agenda_item(item)
                    bill_regex = r"[SAJRPB]+\d+"
                    for bill_match in re.findall(bill_regex, item):
                        agenda_item.add_bill(bill_match)

            match_coordinates(event, {"2 E Main St": (43.07499, -89.38415)})

            yield event
        return

        # if event_count == 0:
        #     raise EmptyScrape

    def extract_field(self, row: str, field: str):
        try:
            return re.findall(
                rf"{field}:\s+'(.*?)'", row, flags=re.MULTILINE | re.DOTALL
            )[0]
        except IndexError:
            return None
