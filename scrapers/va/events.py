from openstates.scrape import Scraper, Event
import dateutil
import json
import pytz
import re


class VaEventScraper(Scraper):
    _tz = pytz.timezone("America/New_York")

    def scrape(self):
        # TODO: what's the deal with this WebAPIKey, will it expire?
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "WebAPIKey": "FCE351B6-9BD8-46E0-B18F-5572F4CCA5B9",
        }

        url = "https://lis.virginia.gov/Schedule/api/GetScheduleListAsync?startDate=10/10/2024%2000:00:00"
        page = self.get(url, verify=False, headers=headers)
        page = json.loads(page.content)
        for row in page["Schedules"]:
            status = "tentative"
            name = row["OwnerName"].strip()

            # them seem to set all the dates to noon then
            # add the actual time to a seperate field.
            when_date = row["ScheduleDate"].replace("T12:00:00", "")
            when_time = row["ScheduleTime"]

            when = dateutil.parser.parse(f"{when_date} {when_time}")
            when = self._tz.localize(when)

            if "RoomDescription" in row:
                location = row["RoomDescription"]
            else:
                location = row["Description"]

            if location == "":
                location = "See Agenda"

            if row["IsCancelled"]:
                status = "cancelled"

            event = Event(
                name=name,
                start_date=when,
                classification="committee-meeting",
                location_name=location,
                status=status,
                description=row["Description"],
            )
            event.add_source("https://lis.virginia.gov/schedule")

            if row["ScheduleFiles"]:
                if len(row["ScheduleFiles"]) > 1:
                    self.warning(
                        "Multiple agenda attachments found, code for this case."
                    )

                event.add_document(
                    "Agenda",
                    row["ScheduleFiles"][0]["FileURL"],
                    media_type="application/pdf",
                )

            if "press conference" not in name.lower():
                if "joint meeting of" in name.lower():
                    coms = name.replace("Joint Meeting of", "")
                    for com in re.split(r",|and", coms, flags=re.I):
                        # the rstrip here catches some trailing dashes
                        com = com.strip().rstrip("- ")
                        if com:
                            event.add_committee(com)
                else:
                    event.add_committee(name.strip())

            yield event
