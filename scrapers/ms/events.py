import dateutil.parser
import pytz
import re
from utils.events import match_coordinates
from openstates.scrape import Scraper
from openstates.scrape import Event
from spatula import PdfPage, HtmlPage
import datetime
import dateutil

TZ = pytz.timezone("US/Central")

start_time_re = re.compile(
    r"^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)", flags=re.IGNORECASE
)
page_number_re = re.compile(r"^page \d+$", flags=re.IGNORECASE)

# Bills have a ". " after each letter in their acronym, so regex is a little long
bill_re = re.compile(
    r"(S\.? ?C\.? ?|S\.? ?N\.? ?|H\.? ?B\.? ?|H\.? ?R\.? ?|S\.? ?B\.? ?|J\.? ?R\.? ?|H\.? ?C\.? ?|S\.? ?R\.? ?).{0,6}?(\d+)"
)


# Finds the required agenda pdf, the url changes yearly
class SenateAgenda(HtmlPage):
    source = "https://www.legislature.ms.gov/calendars-and-schedules/senate-committee-agenda/"

    def process_page(self):
        pdf_link = (
            "https://legislature.ms.gov/media/1151/2024_SENATE_COMMITTEE_AGENDAS.pdf"
        )
        yield from SenateAgendaPdf(source=pdf_link).do_scrape()


# Parses events from a pdf
class SenateAgendaPdf(PdfPage):
    def process_page(self):
        event = None

        # Strip all lines and remove empty lines
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]

        i = 0
        event = None
        while i < len(lines):
            if start_time_re.match(lines[i]):
                # Start date found, next few lines have known data

                # Yield previous event if it exists
                if event:
                    yield event

                date = lines[i]
                time = lines[i + 1]
                committee = lines[i + 2]
                room = lines[i + 3]

                date = date.split(", ", 1)[1]
                time = time.replace(".", "").replace("am", "AM").replace("pm", "PM")
                # AR is after recess, which is undefined
                start_time = f"{date} {time}".replace("AR", "")
                try:
                    start_time = datetime.datetime.strptime(
                        start_time, "%B %d, %Y %I:%M %p"
                    )
                except Exception:
                    start_time = dateutil.parser.parse(start_time)

                location = f"400 High St, Jackson, MS 39201, {room}"
                event = Event(
                    name=committee,
                    start_date=TZ.localize(start_time),
                    location_name=location,
                )
                event.add_source(self.source.url)
                event.add_document("Agenda", url=self.source.url, media_type="pdf")
                event.add_committee(committee)
                match_coordinates(event, {"400 High St": (32.30404, -90.18141)})
                i += 4
            elif bill_re.match(lines[i]):
                # Bill id found
                alpha, num = bill_re.match(lines[i]).groups(1)
                # Remove "." and " " from "S. B."
                alpha = alpha.replace(" ", "").replace(".", "")
                # Recombine both parts of the bill id so it's in the format "SB 123"
                bill = f"{alpha} {num}"
                event.add_bill(bill)
                i += 1
            else:
                # Irrelevant data encountered, can ignore and continue to next line
                i += 1

        # Yield final event if needed
        if event:
            yield event


class MSEventScraper(Scraper):
    def scrape(self):
        yield from self.scrape_house()
        yield from self.scrape_senate()

    def scrape_senate(self):
        return SenateAgenda().do_scrape()

    def scrape_house(self):
        event_url = "https://billstatus.ls.state.ms.us/htms/h_sched.htm"
        text = self.get(event_url).text
        event = None
        when, time, room, com, desc = None, None, None, None, None
        events = set()
        bills_seen = set()

        for line in text.splitlines():
            # new date
            for alpha, num in bill_re.findall(line):
                # Find all bills on this line and format them properly
                # Add them to bills_seen set and hold onto them until an event
                # is about to be added - When an event is added, add all seen
                # bills to it and reset bills_seen back to an empty set
                alpha = alpha.replace(" ", "").replace(".", "")
                bill = f"{alpha} {num}"
                bills_seen.add(bill)

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
                    event_name = f"{com}#{when}#{room}"
                    if event_name in events:
                        self.warning(f"Duplicate event: {event_name}")
                    else:
                        events.add(event_name)
                        event = Event(
                            name=com,
                            start_date=when,
                            location_name=room,
                            classification="committee-meeting",
                            description=desc,
                        )
                        event.dedupe_key = event_name
                        event.add_source(event_url)
                        if self.is_com(com):
                            event.add_committee(name=f"House {com}", note="host")

                        for bill in bills_seen:
                            event.add_bill(bill)
                        # Reset bills_seen so subsequent events don't get bills
                        # from previous events
                        bills_seen = set()

                        match_coordinates(event, {"400 High St": (32.30404, -90.18141)})
                        yield event

                (time, room, com) = re.split(r"\s+", line, maxsplit=2)

                # if it's an after recess/adjourn
                # we can't calculate the time so just leave it empty
                if re.match(r"^(BC|AR|AA|TBA)\+", line):
                    time = ""

                com = com.strip()
                when = dateutil.parser.parse(f"{day} {time}")
                when = TZ.localize(when)

                # reset the description so we can populate it w/
                # upcoming lines (if any)
                desc = ""
            elif when and room and com:
                if line.strip():
                    desc += "\n" + line.strip()

        # don't forget about the last event, which won't get triggered by a new date
        if when and room and com:
            room = f"400 High St, Jackson, MS 39201, Room {room}"
            event_name = f"{com}#{when}#{room}"
            if event_name in events:
                self.warning(f"Duplicate event: {event_name}")
            else:
                events.add(event_name)
                event = Event(
                    name=com,
                    start_date=when,
                    location_name=room,
                    classification="committee-meeting",
                    description=desc,
                )
                event.dedupe_key = event_name
                if self.is_com(com):
                    event.add_committee(name=f"House {com}", note="host")
                match_coordinates(event, {"400 High St": (32.30404, -90.18141)})
                event.add_source(event_url)

                for bill in bills_seen:
                    event.add_bill(bill)
                # Reset bills_seen so subsequent events don't get bills
                # from previous events
                bills_seen = set()

                yield event

    def is_com(self, event_name):
        if "reserved" not in event_name.lower() and "dept of" not in event_name.lower():
            return True
        return False
