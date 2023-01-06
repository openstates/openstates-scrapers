import dateutil.parser
import json
import pytz

from dateutil.parser import ParserError
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


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
            event_count += 1
            yield event

        if event_count < 1:
            raise EmptyScrape
