import datetime
import json
from collections import defaultdict

import dateutil.parser
import lxml.html
import pytz

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


class KSEventScraper(Scraper):
    tz = pytz.timezone("America/Chicago")
    date_range = 30

    def scrape(self, session, start=None):
        self.headers[
            "User-Agent"
        ] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"

        # By default only scrape recent and future events, ignoring older
        # past events. Default the start date to 30 days ago, matching the
        # behavior of the prior implementation.
        if start is None:
            start_date = datetime.date.today() - datetime.timedelta(
                days=self.date_range
            )
        else:
            start_date = dateutil.parser.parse(start).date()

        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )

        slug = meta["_scraped_name"]

        url_root = f"https://www.kslegislature.gov/{slug}/hearings/"

        self.info(f"Using hearings URL: {url_root}")

        landing_page = self.get(url_root).content
        landing_page = lxml.html.fromstring(landing_page)

        available_dates = landing_page.xpath(
            "//div[@id='hearings-cal-root']/@data-available"
        )

        if not available_dates:
            self.warning("No available hearing dates found")
            raise EmptyScrape

        available_dates = json.loads(available_dates[0])

        # Only keep dates on or after the start date.
        available_dates = [
            date_str
            for date_str in available_dates
            if dateutil.parser.parse(date_str).date() >= start_date
        ]

        grouped_events = defaultdict(list)

        for date_str in available_dates:
            page_num = 1

            while True:
                url = (
                    f"{url_root}?page={page_num}"
                    f"&date={date_str}"
                    f"&sort=date"
                    f"&dir=desc"
                    f"&per_page=20"
                )

                page = self.get(url).content
                page = lxml.html.fromstring(page)

                hearings = page.xpath("//table[contains(@class,'site-table')]/tbody/tr")

                self.info(f"Date {date_str}: found {len(hearings)} hearings")

                if not hearings:
                    break

                for hearing in hearings:
                    columns = hearing.xpath("./td")

                    if len(columns) < 7:
                        continue

                    hearing_anchor = columns[0].xpath(".//a")
                    if not hearing_anchor:
                        continue

                    hearing_url = (
                        "https://www.kslegislature.gov"
                        + hearing_anchor[0].attrib["href"]
                    )

                    hearing_date = hearing_anchor[0].text_content().strip()

                    time_str = columns[1].text_content().strip()
                    room = columns[2].text_content().strip()
                    chamber = columns[3].text_content().strip()

                    committee_anchor = columns[4].xpath(".//a")
                    if not committee_anchor:
                        continue

                    committee = committee_anchor[0].text_content().strip()

                    committee_url = (
                        "https://www.kslegislature.gov"
                        + committee_anchor[0].attrib["href"]
                    )

                    bill_id = None
                    bill_url = None

                    bill_anchor = columns[6].xpath(".//a")
                    if bill_anchor:
                        bill_id = bill_anchor[0].text_content().strip()

                        bill_url = (
                            "https://www.kslegislature.gov"
                            + bill_anchor[0].attrib["href"]
                        )

                    when = self.tz.localize(
                        dateutil.parser.parse(f"{hearing_date} {time_str}")
                    )

                    group_key = (
                        when,
                        chamber,
                        committee,
                        room,
                    )

                    grouped_events[group_key].append(
                        {
                            "bill_id": bill_id,
                            "bill_url": bill_url,
                            "hearing_url": hearing_url,
                            "committee_url": committee_url,
                        }
                    )

                next_page = page.xpath(f"//a[contains(@href,'page={page_num + 1}')]")

                if not next_page:
                    break

                page_num += 1

        event_count = 0
        seen = set()

        for (
            when,
            chamber,
            committee,
            room,
        ), bills in grouped_events.items():

            event_name = (f"{chamber}#{committee}#{room}#{when}")[:500]

            if event_name in seen:
                continue

            seen.add(event_name)

            event = Event(
                start_date=when,
                name=f"{chamber} {committee}",
                location_name=room or "Not listed",
            )

            event.dedupe_key = event_name[:499]

            event.add_participant(
                f"{chamber} {committee}",
                type="committee",
                note="host",
            )

            for bill in bills:
                event.add_source(bill["hearing_url"])
                event.add_source(bill["committee_url"])

                if bill["bill_url"]:
                    event.add_source(bill["bill_url"])

                if bill["bill_id"]:
                    agenda = event.add_agenda_item(bill["bill_id"])
                    agenda.add_bill(bill["bill_id"])

            event_count += 1
            yield event

        if event_count < 1:
            raise EmptyScrape
