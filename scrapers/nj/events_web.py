import json
import pytz
from openstates.scrape import Scraper, Event


class NJEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    def clean_location(self, location: str) -> str:
        location = location.replace(
            "State House Annex, Trenton, NJ",
            "State House Annex, 131-137 W State St, Trenton, NJ 08608",
        )
        location = location.replace(
            "Assembly Chambers",
            "Assembly Chambers, New Jersey Statehouse, 125 W State St, Trenton, NJ 08608",
        )
        location = location.replace(
            "Senate Chambers",
            "Senate Chambers, New Jersey Statehouse, 125 W State St, Trenton, NJ 08608",
        )
        return location

    def scrape(self, session=None):
        # year_abr = ((int(session) - 209) * 2) + 2000
        url = "https://www.njleg.state.nj.us/api/schedules"

        json_data = self.get(url).text
        event_list = json.loads(json_data)[0]

        for item in event_list:
            if item["Committee_House"] in ["A", "S", "J"]:
                continue
            name = item["Code_Description"]
            start_date = item["Agenda_Time_Start"]
            end_date = item["Agenda_Time_End"]
            location = item["Agenda_Location"]
            description = item["AgendaComment"] or ""
            link = item["ScheduleLink"]

            status = "tentative"

            if "cancel" in item["ScheduleStatus"]:
                status = "cancelled"
            if item["ScheduleStatus"] == "past":
                status = "passed"

            if location:
                location = self.clean_location(location)
            else:
                location = "New Jersey Statehouse, 125 W State St, Trenton, NJ 08608"

            event = Event(
                name=name,
                start_date=start_date,
                end_date=end_date,
                status=status,
                description=description,
                location_name=location,
            )

            event.add_source(f"https://www.njleg.state.nj.us{link}")

            yield event
