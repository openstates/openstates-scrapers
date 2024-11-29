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
from scrapelib import HTTPError
from spatula import PdfPage, URL

bills_re = re.compile(
    r"(SJR|HCR|HB|HR|SCR|SB|HJR|SR)\s{0,5}0*(\d+)", flags=re.IGNORECASE
)


class Agenda(PdfPage):
    def process_error_response(self, exception):
        # OK has some known 404s for PDFs, so swallow those exceptions
        if isinstance(exception, HTTPError):
            self.logger.warning(f"Skipped PDF download due to to HTTPError {exception}")
        else:
            raise exception

    def process_page(self):
        # Find all bill ids
        bills = bills_re.findall(self.text)

        # Format bills before yielding
        formatted_bills = set()
        for alpha, num in bills:
            formatted_bills.add(f"{alpha.upper()} {num}")

        yield from formatted_bills


class OKEventScraper(Scraper):
    _tz = pytz.timezone("CST6CDT")
    session = requests.Session()

    # usage:
    # poetry run os-update ne \
    # events --scrape start=2022-02-01 end=2022-03-02
    def scrape(self, start=None, end=None):
        yield from self.scrape_senate()

        if start is None:
            delta = datetime.timedelta(days=90)
            start = datetime.date.today() - delta
            start = start.isoformat()

            end = datetime.date.today() + delta
            end = end.isoformat()

        yield from self.scrape_page(start, end)

    def scrape_senate(self):
        # url = "https://oksenate.gov/committee-meetings"
        url = "https://accessible.oksenate.gov/committee-meetings"
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath("//div[contains(@class,'bTiles__items')]/span"):

            if row.xpath(
                "//p[contains(text(), 'There are currently no live Committee Meetings in progress')]"
            ):
                continue

            event_link = row.xpath(".//a[contains(@class,'bTiles__title')]")[0]
            event_title = event_link.xpath("string(.)")
            event_url = event_link.xpath("@href")[0]

            if "legislative session" in event_title.lower():
                continue

            yield from self.scrape_senate_event(event_url)

    def scrape_senate_event(self, url):
        page = lxml.html.fromstring(self.get(url).content)
        page.make_links_absolute(url)

        title = page.xpath("//span[contains(@class,'field--name-title')]/text()")[0]
        try:
            location = page.xpath(
                "//a[contains(@class,'events_custom_timetable')]/text()"
            )[0]
        except IndexError:
            location = "Senate"

        title = f"Senate {title}"
        title = re.sub(r"(2ND|3RD|4TH)* REVISED", "", title).strip()

        if location.lower()[0:4] == "room":
            location = f"2300 N Lincoln Blvd., Oklahoma City, OK 73105 {location}"

        when = page.xpath(
            "//div[contains(@class,'pageIn__infoIt')]/strong/time/@datetime"
        )[0]
        when = dateutil.parser.parse(when)

        event = Event(title, when, location)
        for row in page.xpath("//article//ol/li"):
            item = event.add_agenda_item(row.xpath("string(.)"))
            for bill_link in row.xpath(".//a[contains(@href,'/cf_pdf/')]"):
                item.add_bill(bill_link.xpath("string()"))

        event.add_committee(title)

        event.add_source(url)

        event.add_document("Agenda", url, media_type="text/html")

        match_coordinates(event, {"2300 N Lincoln Blvd": (35.49293, -97.50311)})
        yield event

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
                # Event link currently failing with a 404.
                if (
                    link["route"]
                    == "http://webserver1.lsb.state.ok.us/2023-24HB/CMN-AGRI-20241207-01000000.pdf"
                ):
                    continue
                for bill in Agenda(source=URL(link["route"])).do_scrape():
                    event.add_bill(bill)

            for agenda in meta["agenda"]:
                agenda_text = lxml.html.fromstring(agenda["info"])
                agenda_text = " ".join(agenda_text.xpath("//text()"))
                event.add_agenda_item(agenda_text)

                if agenda["measure"]["data"]:
                    self.info(agenda["measure"])
                    self.error(
                        "Finally found an agenda with linked measure. Modify the code to handle it."
                    )

            yield event

        current_max = offset + limit
        if page["events"]["meta"]["pagination"]["total"] > current_max:
            yield from self.scrape_page(start, end, offset + limit, limit)
