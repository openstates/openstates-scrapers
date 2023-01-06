import dateutil.parser
import pytz
import re
from utils.events import match_coordinates
from openstates.scrape import Scraper
from openstates.scrape import Event


class MSEventScraper(Scraper):
    _tz = pytz.timezone("US/Central")
    chamber_abbrs = {"upper": "s", "lower": "h"}
    chamber_names = {"upper": "Senate", "lower": "House"}

    def scrape(self):
        for chamber in ["upper", "lower"]:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        chamber_abbr = self.chamber_abbrs[chamber]
        event_url = f"http://billstatus.ls.state.ms.us/htms/{chamber_abbr}_sched.htm"
        text = self.get(event_url).text
        event = None

        when, time, room, com, desc = None, None, None, None, None

        for line in text.splitlines():
            # new date
            if re.match(
                r"^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)",
                line,
                re.IGNORECASE,
            ):
                day = line.split("   ")[0].strip()
            # timestamp, start of a new event
            if re.match(r"^\d{2}:\d{2}", line) or re.match(r"^(BC|AR|AA|TBA)\+", line):
                # if there's an event from the previous lines, yield it
                if when and room and com:
                    room = f"400 High St, Jackson, MS 39201, Room {room}"
                    event = Event(
                        name=com,
                        start_date=when,
                        location_name=room,
                        classification="committee-meeting",
                        description=desc,
                    )
                    event.add_source(event_url)
                    if self.is_com(com):
                        event.add_committee(
                            name=f"{self.chamber_names[chamber]} {com}", note="host"
                        )
                    match_coordinates(event, {"400 High St": (32.30404, -90.18141)})
                    yield event

                (time, room, com) = re.split(r"\s+", line, maxsplit=2)

                # if it's an after recess/adjourn
                # we can't calculate the time so just leave it empty
                if re.match(r"^(BC|AR|AA|TBA)\+", line):
                    time = ""

                com = com.strip()
                when = dateutil.parser.parse(f"{day} {time}")
                when = self._tz.localize(when)

                # reset the description so we can populate it w/
                # upcoming lines (if any)
                desc = ""
            elif when and room and com:
                if line.strip():
                    desc += "\n" + line.strip()

        # don't forget about the last event, which won't get triggered by a new date
        if when and room and com:
            room = f"400 High St, Jackson, MS 39201, Room {room}"
            event = Event(
                name=com,
                start_date=when,
                location_name=room,
                classification="committee-meeting",
                description=desc,
            )
            if self.is_com(com):
                event.add_committee(
                    name=f"{self.chamber_names[chamber]} {com}", note="host"
                )
            match_coordinates(event, {"400 High St": (32.30404, -90.18141)})
            event.add_source(event_url)
            yield event

    def is_com(self, event_name):
        if "reserved" not in event_name.lower() and "dept of" not in event_name.lower():
            return True
        return False
