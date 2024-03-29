from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape
from dateutil import parser, relativedelta
import datetime
import pytz
import re
from utils.events import set_location_url, match_coordinates


class WYEventScraper(Scraper):
    _tz = pytz.timezone("America/Denver")
    base_url = "https://web.wyoleg.gov/"
    document_base_url = "https://wyoleg.gov/"

    def scrape(self):
        today = datetime.datetime.today()

        url = "https://web.wyoleg.gov/LsoService/api/Calendar/Events/{}{}01"
        event_count = 0

        # this month and the next 2 months
        events = set()
        for add in [-2, -1, 0, 1, 2]:
            test_date = today + relativedelta.relativedelta(months=+add)
            month_url = url.format(str(test_date.year), str(test_date.month).zfill(2))
            page = self.get(month_url).json()
            for row in page:
                if row["meetingKind"] != 2:
                    continue
                com = f"{row['meetingType']} {row['committee']['fullName']}"
                # skip state holidays or other non-committee hearings
                if com.strip() == "":
                    continue

                start = parser.parse(row["startDate"])
                start = self._tz.localize(start)
                end = parser.parse(row["endTime"])
                end = self._tz.localize(end)

                where = f"{row['address1']} {row['address2']} {row['address3']}".strip()

                if where == "":
                    where = "TBD"

                desc = row["purpose"]
                event_name = f"{com}#{where}#{start}#{end}"
                if event_name in events:
                    self.warning(f"Skipping duplicate event: {event_name}")
                    continue
                events.add(event_name)
                event = Event(
                    name=com,
                    location_name=where,
                    start_date=start,
                    end_date=end,
                    classification="committee-meeting",
                    description=desc,
                )
                event.dedupe_key = event_name
                event.add_committee(com, note="host")

                for media in row["meetingMedias"]:
                    # all these i've seen say they're octet stream but are actually youtube links
                    event.add_media_link(
                        media["documentType"],
                        media["filePath"],
                        "text/html",
                        on_duplicate="ignore",
                    )

                if row["participantURL"]:
                    set_location_url(event, row["participantURL"])

                match_coordinates(event, {"State Capitol": (41.14105, -104.82015)})

                for doc in row["meetingDocuments"]:
                    event.add_document(
                        doc["title"],
                        f"{self.document_base_url}{doc['documentUrl']}",
                        on_duplicate="ignore",
                    )

                for item in row["meetingAgendas"]:
                    self.parse_agenda_item(event, item)

                bills_agenda_item = None
                for bill in row["sessionMeetingBills"]:
                    if bills_agenda_item is None:
                        bills_agenda_item = event.add_agenda_item(
                            "Bills under Consideration"
                        )
                    # Separate "SF" from "0012" in "SF0012" to strip leading zeroes
                    num_match = re.search(r"([A-Z]+)(\d+)", bill["billNumber"])
                    if num_match:
                        bills_agenda_item.add_bill(
                            num_match[1] + " " + num_match[2].lstrip("0")
                        )
                    else:
                        bills_agenda_item.add_bill(bill["billNumber"])

                web_url = "https://www.wyoleg.gov/Calendar/{year}{month}01/Meeting?type=committee&id={meeting_id}"
                web_url = web_url.format(
                    year=str(test_date.year),
                    month=str(test_date.month).zfill(2),
                    meeting_id=row["id"],
                )

                event.add_source(web_url)

                event_count += 1
                yield event

        if event_count < 1:
            raise EmptyScrape

    def parse_agenda_item(self, event, item):
        agenda = event.add_agenda_item(item["title"])
        for presenter in item["meetingPresenters"]:
            name = presenter["name"]
            if presenter["organization"] != "":
                name = f"{name} ({presenter['organization']})"
            agenda.add_person(name)

        for doc in item["meetingDocuments"]:
            event.add_document(
                doc["title"],
                f"{self.document_base_url}{doc['documentUrl']}",
                on_duplicate="ignore",
            )

        for doc in item["budgetMeetingDocuments"]:
            event.add_document(
                doc["displayTitle"],
                f"{self.document_base_url}{doc['documentUrl']}",
                on_duplicate="ignore",
            )

        for sub_item in item["subAgendaItems"]:
            self.parse_agenda_item(event, sub_item)
