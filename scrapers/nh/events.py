# http://www.gencourt.state.nh.us/statstudcomm/details.aspx?id=61&txtchapternumber=541-A%3a2

from utils import LXMLMixin
import dateutil.parser
import pytz
import json
import lxml
import datetime
from openstates.scrape import Scraper, Event


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
        url = f"http://gencourt.state.nh.us/{chamber_names[chamber]}/schedule/CalendarWS.asmx/GetEvents"
        page = self.get(
            url,
            headers={
                "Accept": "Accept: application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json; charset=utf-8",
                "Referer": f"http://gencourt.state.nh.us/{chamber_names[chamber]}/schedule/dailyschedule.aspx",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
            },
        )

        page = json.loads(page.content)
        # real data is double-json encoded string in the 'd' key
        page = json.loads(page["d"])

        # print(page)

        # event_root = "http://gencourt.state.nh.us/senate/schedule"
        event_root = f"https://gencourt.state.nh.us/{chamber_names[chamber]}/schedule"
        event_objects = set()

        for row in page:
            status = "tentative"
            event_url = "{}/{}".format(event_root, row["url"])

            start = dateutil.parser.parse(row["start"])
            start = self._tz.localize(start)
            end = dateutil.parser.parse(row["end"])
            end = self._tz.localize(end)

            if "cancelled" in row["title"] or "canceled" in row["title"]:
                status = "cancelled"

            if start < self._tz.localize(datetime.datetime.now()):
                status = "passed"

            title = row["title"].split("\n")[0].strip()

            if "committee" in title.lower():
                classification = "committee-meeting"
            else:
                classification = "other"

            location = row["title"].split(":")[-1].strip()

            event_name = f"{event_url}#{location}#{start}"
            if event_name in event_objects:
                self.warning(f"Duplicate event {event_name}. Skipping.")
                continue
            event_objects.add(event_name)

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

            self.scrape_event_details(event, event_url)
            yield event

    def scrape_event_details(self, event, url):
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath('//table[@id="gvDetails"]/tr'):
            when = row.xpath("td[1]")[0].text_content().strip()
            item = row.xpath("td[3]")[0].text_content().strip()
            bill_id = row.xpath(
                './/a[contains(@href, "bill_Status/bill_docket")]/text()'
            )[0]
            agenda = event.add_agenda_item(f"{when} {item}")
            agenda.add_bill(bill_id)
