import datetime
import json
import pytz

from pupa.scrape import Scraper, Event


class VTEventScraper(Scraper):
    TIMEZONE = pytz.timezone("America/New_York")

    def scrape(self, session=None):
        if session is None:
            session = self.latest_session()
        year_slug = self.jurisdiction.get_year_slug(session)

        url = "http://legislature.vermont.gov/committee/loadAllMeetings/{}".format(
            year_slug
        )

        json_data = self.get(url).text
        events = json.loads(json_data)["data"]

        for info in events:
            # Determine when the committee meets
            if (
                info["TimeSlot"] == ""
                or info["TimeSlot"] == "1"
                or info["TimeSlot"] == 1
            ):
                start_time = datetime.datetime.strptime(
                    info["MeetingDate"], "%A, %B %d, %Y"
                )
                all_day = True
            else:
                try:
                    start_time = datetime.datetime.strptime(
                        info["MeetingDate"] + ", " + info["TimeSlot"],
                        "%A, %B %d, %Y, %I:%M %p",
                    )
                except ValueError:
                    start_time = datetime.datetime.strptime(
                        info["MeetingDate"] + ", " + info["StartTime"],
                        "%A, %B %d, %Y, %I:%M %p",
                    )
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

            yield event
