# http://www.gencourt.state.nh.us/statstudcomm/details.aspx?id=61&txtchapternumber=541-A%3a2

from utils import LXMLMixin
import dateutil.parser
import pytz
import json
import lxml
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
        if chamber == "upper":
            yield from self.scrape_upper()
        elif chamber == "lower":
            yield from self.scrape_lower()

    def scrape_lower(self):
        yield {}

    def scrape_upper(self):
        # http://gencourt.state.nh.us/dynamicdatafiles/Committees.txt?x=20201216031749
        url = "http://gencourt.state.nh.us/senate/schedule/CalendarWS.asmx/GetEvents"
        page = self.get(
            url,
            headers={
                "Accept": "Accept: application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json; charset=utf-8",
                "Referer": "http://gencourt.state.nh.us/senate/schedule/dailyschedule.aspx",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
            },
        )

        page = json.loads(page.content)
        # real data is double-json encoded string in the 'd' key
        page = json.loads(page["d"])

        event_root = "http://gencourt.state.nh.us/senate/schedule"

        for row in page:
            event_url = "{}/{}".format(event_root, row["url"])

            start = dateutil.parser.parse(row["start"])
            start = self._tz.localize(start)
            end = dateutil.parser.parse(row["end"])
            end = self._tz.localize(end)

            title = row["title"].strip()

            event = Event(
                name=title, start_date=start, end_date=end, location_name="See Source",
            )

            event.add_source(event_url)

            self.scrape_upper_details(event, event_url)
            yield event

    def scrape_upper_details(self, event, url):
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
