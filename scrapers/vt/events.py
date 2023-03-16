import dateutil.parser
import json
import pytz

from dateutil.parser import ParserError
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

from spatula import JsonPage, URL


def scrape_bills(year_slug, committee_id, session_id):
    # 4 endpoints are used for different types of bills
    bill_types = [
        "loadBillsIn",
        "loadBillsOut",
        "loadSponsoredBills",
        "loadReferredBills",
    ]

    # Add bills to a set to remove duplicate bills
    bills = set()
    for bill_type in bill_types:
        source = f"https://legislature.vermont.gov/committee/{bill_type}/{year_slug}?committeeId={committee_id}&sessionId={session_id}"
        info = BillsInfo(source=URL(source))
        for bill in info.do_scrape():
            bills.add(bill)
    yield from bills


class BillsInfo(JsonPage):
    example_source = "https://legislature.vermont.gov/committee/loadBillsOut/2024?committeeId=189&sessionId=8"

    def process_page(self):
        # Bill number is in format "J.R.H.123"
        resp = self.response.json()
        for bill in resp["data"]:
            # Split on final "." to separate letter and number portion
            alpha, num = bill["BillNumber"].rsplit(".", 1)
            # Remove "." from letter portion
            alpha = alpha.replace(".", "")
            # Recombine with a single space between letters and numbers
            yield f"{alpha} {num}"


class VTEventScraper(Scraper):
    TIMEZONE = pytz.timezone("America/New_York")

    def scrape(self, session=None):
        year_slug = self.jurisdiction.get_year_slug(session)

        url = "http://legislature.vermont.gov/committee/loadAllMeetings/{}".format(
            year_slug
        )

        json_data = self.get(url).text
        event_count = 0
        events = json.loads(json_data)["data"]

        for info in events:
            # Determine when the committee meets
            if (
                info["TimeSlot"] == ""
                or info["TimeSlot"] == "1"
                or info["TimeSlot"] == 1
            ):
                start_time = dateutil.parser.parse(info["MeetingDate"])
                all_day = True
            else:
                try:
                    start_time = dateutil.parser.parse(
                        f"{info['MeetingDate']}, {info['TimeSlot']}"
                    )
                except ParserError:
                    start_time = dateutil.parser.parse(info["MeetingDate"])

                all_day = False

            event = Event(
                start_date=self.TIMEZONE.localize(start_time),
                all_day=all_day,
                name="Meeting of the {}".format(info["LongName"]),
                description="committee meeting",
                location_name="{0}, Room {1}".format(
                    info["BuildingName"], info["RoomNbr"]
                ),
            )
            event.add_source(url)
            event.add_committee(name=info["LongName"], note="host")

            # Find all bills and add them to the event
            committee_id = info["CommitteeID"]
            session_id = info["PermanentID"]
            for bill in scrape_bills(year_slug, committee_id, session_id):
                event.add_bill(bill)

            event_count += 1
            yield event

        if event_count < 1:
            raise EmptyScrape
