import pytz
import datetime

from dateutil import parser
from dateutil.relativedelta import relativedelta
from openstates.scrape import Scraper, Event
from utils.events import month_range


class DCEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    bill_prefixes = {"bill": "B", "resolution": "R"}

    events_seen = []

    def scrape(self, start_date=None, end_date=None):

        if start_date is None:
            start_date = datetime.date.today() + relativedelta(months=-3)
        else:
            start_date = parser.parse(start_date)

        if end_date is None:
            end_date = datetime.date.today() + relativedelta(months=+3)
        else:
            end_date = parser.parse(start_date)

        for d in month_range(start_date, end_date):
            data = self.scrape_month_json(d.month, d.year)
            for row in data:
                yield from self.parse_event(row)

        # note: there is also https://lims.dccouncil.gov/Hearings/API/Public/GetUpcomingHearings
        # but that just seems to be a worse version of GetHearingsCalendar,
        # as it doesn't have any more info and lacks structured agendas

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

        # Once in a while DC has a semi-duplicate event
        # even though URLs and upstream IDs are different
        # so we append ID into title when collision occurs
        event_title = row["hearingTitle"]
        event_dupe_key = f"{event_title}-{when}"
        if event_dupe_key in self.events_seen:
            event_title = f"{event_title} ({row['hearingId']})"
        else:
            self.events_seen.append(event_dupe_key)

        e = Event(event_title, when, where, upstream_id=str(row["hearingId"]))

        e.add_source(f"https://lims.dccouncil.gov/Hearings/hearings/{row['hearingId']}")

        e.add_committee(row["hearingTitle"])

        for topic in row["topics"]:
            # some topics have a structured obj, some are just strings
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
