import re
import datetime
import dateutil.parser
import pytz
from utils import LXMLMixin
from utils.events import match_coordinates
from openstates.scrape import Scraper, Event


class UTEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("MST7MDT")
    base_url = "https://le.utah.gov"

    def scrape(self, chamber=None):
        url = "https://le.utah.gov/CalServ/CalServ?month={}&year={}"

        year = datetime.datetime.today().year

        for i in range(0, 12):
            page = self.get(url.format(i, year)).json()
            if "days" in page:
                for day_row in page["days"]:
                    for row in day_row["events"]:
                        # ignore 'note', 'housefloor', 'senatefloor'
                        if row["type"] == "meeting":
                            status = "tentative"
                            title = row["desc"]
                            where = row["location"]

                            if "state capitol" in where.lower():
                                where = (
                                    f"{where}, 350 State St, Salt Lake City, UT 84103"
                                )
                            elif re.match(
                                r"(.*) (House|Senate) Building",
                                where,
                                flags=re.IGNORECASE,
                            ):
                                where = f"{where}, Utah State Capitol, 350 State St, Salt Lake City, UT 84103"

                            when = dateutil.parser.parse(
                                f"{day_row['year']}-{str(int(day_row['month'])+1)}-{day_row['day']} {row['time']}"
                            )

                            when = self._tz.localize(when)

                            if "status" in row and row["status"] == "C":
                                status = "cancelled"

                            event = Event(
                                name=title,
                                location_name=where,
                                start_date=when,
                                classification="committee-meeting",
                                status=status,
                            )

                            event.add_committee(title, note="host")

                            if "agenda" in row:
                                event.add_document(
                                    "Agenda",
                                    f"{self.base_url}{row['agenda']}",
                                    media_type="text/html",
                                    on_duplicate="ignore",
                                )

                            if "minutes" in row:
                                event.add_document(
                                    "Minutes",
                                    f"{self.base_url}{row['minutes']}",
                                    media_type="text/html",
                                    on_duplicate="ignore",
                                )

                            if "mediaurl" in row:
                                event.add_media_link(
                                    "Media",
                                    f"{self.base_url}{row['mediaurl']}",
                                    media_type="text/html",
                                    on_duplicate="ignore",
                                )
                                if re.findall(r"mtgID=(\d+)", row["mediaurl"]):
                                    hearing_id = re.findall(
                                        r"mtgID=(\d+)", row["mediaurl"]
                                    )[0]
                                    docs_url = f"https://glen.le.utah.gov/committees/meeting/{hearing_id}/1234"
                                    docs_page = self.get(docs_url).json()
                                    if "meetingMaterials" in docs_page:
                                        for mat in docs_page["meetingMaterials"]:
                                            agenda = event.add_agenda_item(
                                                mat["description"]
                                            )
                                            event.add_document(
                                                mat["description"],
                                                f"{self.base_url}{mat['docUrl']}",
                                                media_type="application/pdf",
                                                on_duplicate="ignore",
                                            )

                                            for bill_row in re.findall(
                                                r"(\w{2,3}\d{4})", mat["description"]
                                            ):
                                                agenda.add_bill(bill_row)

                                    # NOTE: The following data appears to be duped on the meetingMaterials endpoint
                                    # but leaving this in place commented out, in case that ever changes.
                                    #
                                    # rather than return an empty object this page just times out if there are no bills
                                    # so don't retry, and pass on failure
                                    # bills_url = f"https://glen.le.utah.gov/agencal/{hearing_id}/1234"
                                    # self.retry_attempts = 0
                                    # try:
                                    #     bills_page = self.get(bills_url, timeout=3).json()
                                    #     if 'agendaitems' in bills_page:
                                    #         for bill_row in bills_page['agendaitems']:

                                    #             agenda = event.add_agenda_item(bill_row['description'])
                                    #             if 'bill' in bill_row:
                                    #                 agenda.add_bill(bill_row['bill'])
                                    #                 print(bill_row)
                                    # except requests.exceptions.ReadTimeout:
                                    #     pass

                                    # then reset the retry attempts to normal for other requests
                                    self.retry_attempts = 3

                            source_url = f"{self.base_url}{row['itemurl']}"
                            event.add_source(source_url)

                            match_coordinates(
                                event,
                                {
                                    "House Building": (40.77809, -111.88901),
                                    "Senate Building": (40.77806, -111.88735),
                                    "State Capitol": (40.77745, -111.88815),
                                },
                            )

                            yield event
