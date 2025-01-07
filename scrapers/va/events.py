from openstates.scrape import Scraper, Event
import datetime
import dateutil
import json
import pytz
import re


simple_html_tag_regex = re.compile("<.*?>")


class VaEventScraper(Scraper):
    _tz = pytz.timezone("America/New_York")

    def scrape(self, start_date=None):
        # TODO: what's the deal with this WebAPIKey, will it expire?
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "WebAPIKey": "FCE351B6-9BD8-46E0-B18F-5572F4CCA5B9",
        }

        # e.g. 10/10/2024
        if start_date:
            start_date = dateutil.parser.parse(start_date).strftime("%m/%d/%Y")
        else:
            start_date = datetime.datetime.today().strftime("%m/%d/%Y")

        url = f"https://lis.virginia.gov/Schedule/api/GetScheduleListAsync?startDate={start_date}%2000:00:00"
        page = self.get(url, verify=False, headers=headers)
        page = json.loads(page.content)
        for row in page["Schedules"]:
            status = "tentative"
            name = row["OwnerName"].strip()

            if name == "":
                name = row["Description"].split(";")[0].strip()

            # them seem to set all the dates to noon then
            # add the actual time to a seperate field.
            when_date = row["ScheduleDate"].replace("T12:00:00", "")
            when_time = row["ScheduleTime"]

            # sometimes the site JSON contains this string
            if when_time == "Invalid date":
                when_time = ""

            when = dateutil.parser.parse(f"{when_date} {when_time}")
            when = self._tz.localize(when)

            if "RoomDescription" in row:
                location = row["RoomDescription"]
            else:
                # the Description property is kinda sloppy, it can have a little overlapping title
                # and sometimes links to the agenda and livestream
                # so need to strip: anything in HTML tags (location seems to never be bolded or in link)
                location = re.sub(simple_html_tag_regex, "", row["Description"])[:200]

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

            for ct, attach in enumerate(row["ScheduleFiles"]):
                if ct == 0:
                    event.add_document(
                        "Agenda",
                        attach["FileURL"],
                        media_type="application/pdf",
                    )
                else:
                    event.add_document(
                        f"Attachment {ct}",
                        attach["FileURL"],
                        media_type="application/pdf",
                    )

            if "press conference" not in name.lower():
                if "joint meeting of" in name.lower():
                    coms = name.replace("Joint Meeting of", "")
                    # "joint meeting of com 1, com2 and com3"
                    # becomes ['com 1', 'com2', 'com3']
                    for com in re.split(r",|and", coms, flags=re.I):
                        # the rstrip here catches some trailing dashes
                        com = com.strip().rstrip("- ")
                        if com:
                            event.add_committee(com)
                else:
                    event.add_committee(name.strip())

            yield event
