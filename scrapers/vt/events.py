import datetime
import re
import dateutil.parser
import json
import pytz

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

from spatula import CSS, HtmlPage, XPath

TIMEZONE = pytz.timezone("America/New_York")


class VTAgendaOfWeek(HtmlPage):
    example_source = "https://legislature.vermont.gov/committee/agenda/2024/005917.htm"

    def process_page(self):
        info = self.input
        members = []
        for row in CSS("#heading .align-right ul li").match(self.root, min_items=0):
            member_name = row.text_content()
            member_name = member_name.split(".")[1]
            position = (
                member_name.split(",")[1].lower() if "," in member_name else "member"
            )
            member_name = member_name.split(",")[0].replace("\t", "").replace("\n", "")
            members.append([member_name, position])

        bill_id_regex = re.compile(r"((H|S)\.\s?[0-9]+)")
        for event_row in CSS(".csD273B8C5").match(self.root, min_items=0):
            start_date = event_row.text_content().strip() or ""
            start_time = (
                XPath("following-sibling::p[1]/span[1]")
                .match_one(event_row)
                .text_content()
                .strip()
            )
            start_time = start_time if "AM" in start_time or "PM" in start_time else ""
            start_date = f"{start_date} {start_time}".strip()
            if not start_date:
                continue
            start_date = dateutil.parser.parse(start_date)
            event = Event(
                start_date=TIMEZONE.localize(start_date),
                name="Meeting of the {}".format(info["LongName"]),
                description="committee meeting",
                location_name="{0}, Room {1}".format(
                    info["BuildingName"], info["RoomNbr"]
                ),
            )
            event.add_source(self.source.url)
            committe_name = info["LongName"].strip()
            event.add_committee(name=committe_name, note="host")
            for member in members:
                event.add_person(member[0], note=member[1])

            bills_mentioned = set()
            for row in XPath("following-sibling::p").match(event_row, min_items=0):
                style = row.get("style")
                if style and "tab-stop" in style:
                    break
                row_text = row.text_content()
                bill_id = bill_id_regex.search(row_text)

                if bill_id:
                    bill_id = bill_id.group(1).replace(".", "").strip()
                    if bill_id and bill_id not in bills_mentioned:
                        event.add_bill(bill_id)
                        bills_mentioned.add(bill_id)

            yield event


class VTEventScraper(Scraper):
    def scrape(self, session=None):
        year_slug = self.jurisdiction.get_year_slug(session)

        url = "http://legislature.vermont.gov/committee/loadAllMeetings/{}".format(
            year_slug
        )

        json_data = self.get(url).text
        events = json.loads(json_data)["data"]
        event_count = 0
        # This should be some point in the past, because some event agendas actually include dates
        # that are later than the info["MeetingDate"] (which is just a day, has no time info)
        # setting to a week ago to ensure we get the most current/near-future events possible
        parse_events_after_date = datetime.datetime.today() - datetime.timedelta(days=7)
        for info in events:
            # Determine when the committee meets
            start_time = dateutil.parser.parse(info["MeetingDate"])
            if start_time < parse_events_after_date:
                continue

            if "htm" in info["AgendaName"]:
                meeting_id = info["CommitteeMeetingID"]
                source = f"https://legislature.vermont.gov/committee/agenda/{year_slug}/{meeting_id}"
                events = VTAgendaOfWeek(info, source=source)
                try:
                    yield from events.do_scrape()
                except Exception as e:
                    self.warning(e)
                    continue
                event_count += 1

        if event_count == 0:
            raise EmptyScrape("No events")
