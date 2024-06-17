import re
import dateutil.parser
import pytz

from lxml import html
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

from spatula import CSS, HtmlPage, XPath

TIMEZONE = pytz.timezone("America/New_York")


class VTAgendaOfWeek(HtmlPage):
    example_source = "https://legislature.vermont.gov/committee/agenda/2024/5917"

    def process_page(self):
        members = []
        for row in CSS("#heading .align-right ul li", min_items=0).match(self.root):
            member_name = row.text_content()
            member_name = member_name.split(".")[1]
            position = (
                member_name.split(",")[1].lower() if "," in member_name else "member"
            )
            member_name = member_name.split(",")[0].replace("\t", "").replace("\n", "")
            members.append([member_name, position])

        bill_id_regex = re.compile(r"((H|S)\.\s?[0-9]+)")
        committe_name = CSS(".cs16C7EBC2").match_one(self.root).text_content().strip()

        room_number = (
            XPath('//span[contains(text(), "Room")]')
            .match(self.root)[0]
            .text_content()
            .replace("and Zoom", "")
            .strip()
        )
        building_name = "State House"
        time_period = (
            XPath('//p[./span[contains(text(), "Room")]]/following-sibling::p[1]/span')
            .match(self.root)[0]
            .text_content()
            .strip()
        )
        for event_row in CSS(".csD273B8C5", min_items=0).match(self.root):
            start_date = event_row.text_content().strip() or time_period
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
                name="Meeting of the {}".format(committe_name),
                description="committee meeting",
                location_name="{0}, {1}".format(building_name, room_number),
            )
            event.add_source(self.source.url)
            event.dedupe_key = f"{start_date}#{committe_name}#{self.source.url}"
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

        url = "https://legislature.vermont.gov/committee/meetings/{}".format(year_slug)

        doc = html.fromstring(self.get(url).text)
        doc.make_links_absolute(url)
        event_count = 0
        # This should be some point in the past, because some event agendas actually include dates
        # that are later than the info["MeetingDate"] (which is just a day, has no time info)
        # setting to a week ago to ensure we get the most current/near-future events possible

        for source in doc.xpath('//a[contains(@href, "/agenda/")]/@href'):
            # Determine when the committee meets
            events = VTAgendaOfWeek(source=source)
            try:
                yield from events.do_scrape()
            except Exception as e:
                self.warning(e)
                continue
            event_count += 1

        if event_count == 0:
            raise EmptyScrape("No events")
