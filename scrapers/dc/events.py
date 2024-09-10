import lxml.html
import pytz
import re
from dateutil import parser
from dateutil.relativedelta import relativedelta
import datetime
import itertools
import operator

from ics import Calendar
from openstates.scrape import Scraper, Event
from utils.media import get_media_type


class DCEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    bill_prefixes = {"bill": "B", "resolution": "R"}

    def scrape(self, start_date=None, end_date=None):

        if start_date is None:
            start_date = datetime.date.today() + relativedelta(months=-3)
        else:
            start_date = parser.parse(start_date)

        if end_date is None:
            end_date = datetime.date.today() + relativedelta(months=+3)
        else:
            end_date = parser.parse(start_date)

        for d in self.month_range(start_date, end_date):
            data = self.scrape_month_json(d.month, d.year)
            for row in data:
                yield from self.parse_event(row)

    def scrape_month_json(self, month: int, year: int):
        self.info(f"Scraping {str(year)}-{str(month)}")
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
        }

        json_data = {
            "month": month,
            "year": year,
            "committeeId": 0,
            "searchText": "",
        }

        response = self.post(
            "https://lims.dccouncil.gov/Hearings/API/Public/GetHearingsCalendar",
            headers=headers,
            json=json_data,
        )
        return response.json()

    def parse_event(self, row):
        when = parser.parse(row["hearingDateTime"])
        when = self._tz.localize(when)

        where = f"{row['locationAddress']} {row['location']}".strip()

        e = Event(row["hearingTitle"], when, where, upstream_id=str(row["hearingId"]))

        e.add_source(f"https://lims.dccouncil.gov/Hearings/hearings/{row['hearingId']}")

        e.add_committee(row["hearingTitle"])

        for topic in row["topics"]:
            agenda_row = e.add_agenda_item(topic["topic"])

            if topic["legislationNumber"]:
                agenda_row.add_bill(topic["legislationNumber"])

        if row["witnessListAttachment"]:
            list_url = f"https://lims.dccouncil.gov/Hearings/API/Public/DownloadAttachment/{row['witnessListAttachment']['attachmentGuid']}"
            e.add_document(
                row["witnessListAttachment"]["attachmentName"],
                list_url,
                media_type="application/pdf",
            )

        yield e

    def old_scrape(self):
        # use ical to get the full feed and start dates, which aren't cleanly in the html
        ical_url = (
            "https://dccouncil.gov/?post_type=tribe_events&ical=1&eventDisplay=list"
        )

        ical = self.get(ical_url).text
        self.info("Parsing event feed. This may take a moment.")
        cal = Calendar(ical)
        for e in cal.events:
            yield from self.scrape_cal_page(e)

    def scrape_cal_page(self, e):
        # scrape the html to get the correct links and description
        page = lxml.html.fromstring(self.get(e.url).content)

        title = e.name
        start = str(e.begin)
        location = e.location
        description = str(e.description)

        event = Event(
            title,
            start,
            location,
            description=description,
            end_date=str(e.end),
        )

        bill_regex = r"(?P<type>Bill|Resolution) (?P<session>\d+)-(?P<billnumber>\d+)"
        matches = re.findall(bill_regex, description, flags=re.IGNORECASE)

        for match in matches:
            bill = (
                f"{self.bill_prefixes[match[0].lower()]} {match[1]}-{match[2].zfill(4)}"
            )
            event.add_bill(bill)

        try:
            header = page.xpath(
                "//header[contains(@class,'article-header')]/p[1]/text()"
            )[0]
        except IndexError:
            header = page.xpath(
                "//header[contains(@class,'article-header')]/h1[1]/text()"
            )[0]
        if "&bullet;" in header:
            com_name = header.split("&bullet;")[1].strip()
            if "whole" not in com_name.lower():
                event.add_participant(com_name, type="committee", note="host")

        materials = page.xpath(
            "//section[contains(@class,'aside-section')]//a[contains(@class,'icon-link')]"
        )
        for mat in materials:
            # sometimes they add broken empty links here
            if mat.xpath("text()"):
                title = mat.xpath("text()")[0].strip()
                url = mat.xpath("@href")[0]
                event.add_document(title, url, media_type=get_media_type(url))

        event.add_source(e.url)

        yield event

    def month_range(
        self,
        start: datetime.date,
        end: datetime.date,
    ):
        """Yields the 1st day of each month in the given date range."""
        yield from itertools.takewhile(
            lambda date: date < end,
            itertools.accumulate(
                itertools.repeat(relativedelta(months=1)),
                operator.add,
                initial=start,
            ),
        )
