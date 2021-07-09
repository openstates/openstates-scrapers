from openstates.scrape import Scraper, Event
from dateutil import parser, relativedelta
import datetime
import pytz


class WYEventScraper(Scraper):
    _tz = pytz.timezone("America/Denver")
    base_url = "https://web.wyoleg.gov/"

    def scrape(self):
        today = datetime.datetime.today()

        url = "https://web.wyoleg.gov/LsoService/api/Calendar/Events/{}{}01"

        # this month and the next 2 months
        for add in [0, 1, 2]:
            test_date = today + relativedelta.relativedelta(months=+add)
            month_url = url.format(str(test_date.year), str(test_date.month).zfill(2))
            page = self.get(month_url).json()
            for row in page:
                if row["meetingKind"] == 2:
                    com = f"{row['meetingType']} {row['committee']['fullName']}"
                    # skip state holidays or other non-committee hearings
                    if com.strip() == "":
                        continue

                    start = parser.parse(row["startDate"])
                    start = self._tz.localize(start)
                    end = parser.parse(row["endTime"])
                    end = self._tz.localize(end)

                    where = row["address1"]

                    if where == "":
                        where = "TBD"

                    desc = row["purpose"]

                    event = Event(
                        name=com,
                        location_name=where,
                        start_date=start,
                        end_date=end,
                        classification="committee-meeting",
                        description=desc,
                    )

                    for media in row["meetingMedias"]:
                        # all these i've seen say they're octet stream but are actually youtube links
                        event.add_media_link(
                            media["documentType"],
                            media["filePath"],
                            "text/html",
                            on_duplicate="ignore",
                        )

                    for doc in row["meetingDocuments"]:
                        event.add_document(
                            doc["title"],
                            f"{self.base_url}{doc['documentUrl']}",
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
                        bills_agenda_item.add_bill(bill["billNumber"])

                    web_url = "https://www.wyoleg.gov/Calendar/{year}{month}01/Meeting?type=committee&id={meeting_id}"
                    web_url = web_url.format(
                        year=str(test_date.year),
                        month=str(test_date.month).zfill(2),
                        meeting_id=row["id"],
                    )

                    event.add_source(web_url)
                    yield event

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
                f"{self.base_url}{doc['documentUrl']}",
                on_duplicate="ignore",
            )

        for doc in item["budgetMeetingDocuments"]:
            event.add_document(
                doc["displayTitle"],
                f"{self.base_url}{doc['documentUrl']}",
                on_duplicate="ignore",
            )

        for sub_item in item["subAgendaItems"]:
            self.parse_agenda_item(event, sub_item)
