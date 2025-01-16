import datetime
import lxml
import pytz
import re

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape
from utils.events import match_coordinates

"""
Nasty regex to clean out sub-elements from divs containing
text we need
"""
re_span = re.compile(r"<span.*?</span>|<div.*?>|</div>")


class NEEventScraper(Scraper):
    _tz = pytz.timezone("US/Central")
    # SSL bad as of 2024-11-18
    verify = False

    # usage: PYTHONPATH=scrapers poetry run os-update ne
    # events --scrape start=2020-02-02 end=2020-03-02
    # or left empty it will default to the next 30 days
    def scrape(self, start=None, end=None):
        LIST_URL = "https://nebraskalegislature.gov/calendar/hearings_range.php"

        now = datetime.datetime.now()

        if start is None:
            start = now
        else:
            start = datetime.datetime.strptime(start, "%Y-%m-%d")

        if end is None:
            end = now + datetime.timedelta(days=30)
        else:
            end = datetime.datetime.strptime(end, "%Y-%m-%d")

        args = {
            "startMonth": start.strftime("%m"),
            "startDay": start.strftime("%d"),
            "startYear": start.strftime("%Y"),
            "endMonth": end.strftime("%m"),
            "endDay": end.strftime("%d"),
            "endYear": end.strftime("%Y"),
        }
        page = self.post(LIST_URL, args, verify=False).content

        yield from self.scrape_events(page)

    def scrape_events(self, page):

        page = lxml.html.fromstring(page)
        page.make_links_absolute("https://nebraskalegislature.gov/")

        if page.xpath(
            "//h3[contains(text(),'There are no hearings for the date range')]"
        ):
            raise EmptyScrape

        for meeting in page.xpath('//div[@class="card mb-4"]'):
            com = meeting.xpath(
                'div[contains(@class, "card-header")]/div/div[1]/text()'
            )[0].strip()

            details = meeting.xpath(
                'div[contains(@class, "card-header")]/small/text()'
            )[0].strip()

            # (location, time)
            location_time_parts = details.split(" - ")
            location = " - ".join(location_time_parts[:-1])
            time = location_time_parts[-1]

            # turn room numbers into the full address
            if location.lower().startswith("room"):
                location = f"1445 K St, Lincoln, NE 68508, {location}"

            day = meeting.xpath("./preceding-sibling::h2[@class='text-center']/text()")[
                -1
            ].strip()

            # Thursday February 27, 2020 1:30 PM
            date = f"{day} {time}"
            event_date = self._tz.localize(
                datetime.datetime.strptime(date, "%A %B %d, %Y %I:%M %p")
            )

            event = Event(
                name=com,
                start_date=event_date,
                classification="committee-meeting",
                description="Committee Meeting",
                location_name=location,
            )

            event.add_committee(com, note="host")
            match_coordinates(event, {"1445 K St": (40.80824, -96.69973)})

            # add documents
            for row in meeting.xpath("table/tr"):
                if row.xpath("th"):
                    # 'th' element found (we skip headers)
                    continue
                details = row.xpath("td/div[@class='row g-0 pb-1']")[0]
                document = re_span.sub(
                    "", lxml.etree.tostring(details.xpath("div")[0]).decode()
                ).strip()
                desc = re_span.sub(
                    "", lxml.etree.tostring(details.xpath("div")[2]).decode()
                ).strip()

                if desc:
                    agenda_item = event.add_agenda_item(description=desc)

                    if document not in ["Appointment"]:
                        bill_id = lxml.html.fromstring(document).text
                        agenda_item.add_bill(bill_id)

                    bill_links = row.xpath(".//a[contains(@href, 'view_bill.php')]")
                    for link in bill_links:
                        agenda_item.add_bill(link.xpath("text()")[0].strip())

            event.add_source("https://nebraskalegislature.gov/calendar/calendar.php")
            yield event
