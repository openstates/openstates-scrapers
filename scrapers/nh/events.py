# https://www.gencourt.state.nh.us/statstudcomm/details.aspx?id=61&txtchapternumber=541-A%3a2

from utils import LXMLMixin
import dateutil.parser
import pytz
import json
import lxml
import datetime
from openstates.scrape import Scraper, Event
from utils.events import match_coordinates
import re

bill_re = re.compile(
    r"([a-z]+)0*(\d+)",
    flags=re.IGNORECASE,
)


# Adds a space and removes any leading zeros from a bill id
# example input: "HB01234", example output: "HB 123"
def format_bill(bill):
    component = bill_re.match(bill)
    return f"{component.group(1)} {component.group(2)}"


class NHEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Eastern")

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            chambers = ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        chamber_names = {"lower": "house", "upper": "senate"}
        # http://gencourt.state.nh.us/dynamicdatafiles/Committees.txt?x=20201216031749
        url = f"https://gc.nh.gov/{chamber_names[chamber]}/schedule/CalendarWS.asmx/GetEvents"
        page = self.get(
            url,
            headers={
                "Accept": "Accept: application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json; charset=utf-8",
                "Referer": f"https://gc.nh.gov/{chamber_names[chamber]}/schedule/dailyschedule.aspx",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
            },
        )

        page = json.loads(page.content)
        # real data is double-json encoded string in the 'd' key
        page = json.loads(page["d"])

        event_root = f"https://gencourt.state.nh.us/{chamber_names[chamber]}/schedule"
        event_objects = set()

        for row in page:
            status = "tentative"
            event_url = "{}/{}".format(event_root, row["url"])

            start = dateutil.parser.parse(row["start"])
            start = self._tz.localize(start)
            end = dateutil.parser.parse(row["end"])
            end = self._tz.localize(end)

            if start < self._tz.localize(datetime.datetime.now()):
                status = "passed"

            title = row["title"].split("\n")[0].strip()

            if "committee" in title.lower():
                classification = "committee-meeting"
            else:
                classification = "other"

            location = row["title"].split(":")[-1].strip()
            location = location.replace(
                "LOB",
                "Legislative Office Building, 33 North State Street, Concord, NH 03301",
            )
            location = location.replace(
                "SH",
                "New Hampshire State House, 107 North Main Street, Concord, NH 03301",
            )

            event_name = f"{event_url}#{location}#{start}"
            if event_name in event_objects:
                self.warning(f"Duplicate event {event_name}. Skipping.")
                continue
            event_objects.add(event_name)

            title = row["title"].split(":")[0].strip()

            title = re.sub(
                r"==(revised|time change|room change)==", "", title, flags=re.IGNORECASE
            )

            if (
                "cancelled" in row["title"].lower()
                or "canceled" in row["title"].lower()
            ):
                status = "cancelled"
                title = re.sub("==Cancell?ed==", "", title, flags=re.IGNORECASE)

            event = Event(
                name=title,
                start_date=start,
                end_date=end,
                location_name=location,
                status=status,
                classification=classification,
            )
            event.dedupe_key = event_name
            event.add_source(event_url)

            if "commission" not in title.lower():
                prefix = chamber_names[chamber].title()
                if title.isupper():
                    prefix = prefix.upper()
                event.add_committee(f"{prefix} {title}")

            self.scrape_event_details(event, event_url)

            match_coordinates(
                event,
                {
                    "Legislative Office Building": ("43.20662", "-71.53938"),
                    "State House": ("43.20699", "-71.53811"),
                },
            )

            yield event

    def scrape_event_details(self, event, url):
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath('//table[@id="pageBody_gvDetails"]/tr'):
            when = row.xpath("td[1]")[0].text_content().strip()
            item = row.xpath("td[3]")[0].text_content().strip()
            bill_id = row.xpath('.//a[contains(@href, "bill_Status/billinfo")]/text()')[
                0
            ]
            bill_id = format_bill(bill_id)
            agenda = event.add_agenda_item(f"{when} {item}")
            agenda.add_bill(bill_id)
