import re
import pytz
import logging
import dateutil.parser
import datetime
from spatula import HtmlPage
from openstates.scrape import Scraper, Event


def time_is_earlier(new, current):
    new_magnitude = int(new[0:2] + new[3:5])
    current_magnitude = int(current[0:2] + current[3:5])
    if new_magnitude < current_magnitude:
        return True
    else:
        return False


class EventConsolidator:
    def __init__(self, items):
        self.items = items
        self.events = {}
        self._tz = pytz.timezone("US/Central")

    def consolidate(self):
        for item in self.items:
            date_time = item["date_time"]
            local_date = dateutil.parser.parse(date_time)

            item_date, item_time = str(local_date).split()

            committee = item["committee"]
            location = item["location"]
            event_key = f"{item_date}-{committee}-{location}"

            if not self.events.get(event_key):
                self.events[event_key] = {}
                self.events[event_key]["event_start_time"] = item_time
                self.events[event_key]["item_keys"] = set()
            else:
                current_start = self.events[event_key]["event_start_time"]
                if time_is_earlier(item_time, current_start):
                    self.events[event_key]["event_start_time"] = item_time

            self.events[event_key]["item_keys"].add(item_time)

            agenda_item_details = {
                "description": item["description"],
                "bill_name": item["bill_name"],
            }
            self.events[event_key][item_time] = []
            self.events[event_key][item_time].append(agenda_item_details)

        print(self.events)
        print(len(self.events))

        yield from self.create_events()

    def create_events(self):
        event_objects = []
        # TODO: Pass url to this class from EventsTable.process_page()
        url = "https://www.ndlegis.gov/legend/committee/hearings/public-schedule/"
        for event in self.events.keys():
            date, com, loc = re.search(r"(.+)\-(.+)\-(.+)", event).groups()
            print(date + com)
            start_time = self.events[event]["event_start_time"]
            date_time = f"{date} {start_time}"
            date_object = dateutil.parser.parse(date_time)
            date_with_offset = self._tz.localize(date_object)

            event_obj = Event(
                name=com,
                location_name=loc,
                description="Standing Committee Hearing",
                start_date=date_with_offset,
            )

            for item_key in self.events[event]["item_keys"]:
                agenda = self.events[event][item_key]
                for item in agenda:
                    time = datetime.datetime.strptime(item_key, "%H:%M:%S").strftime(
                        "%I:%M %p"
                    )
                    descr_with_time = f"[{time}]: {item['description']}"
                    item_descr = event_obj.add_agenda_item(descr_with_time)
                    item_descr.add_bill(item["bill_name"])

            event_obj.add_source(url)

            event_objects.append(event_obj)

        return event_objects


class EventsTable(HtmlPage):
    events_path = "/legend/committee/hearings/public-schedule/"
    source = f"https://www.ndlegis.gov{events_path}"

    def process_page(self):
        date_span = self.root.xpath(".//h5[2]")[0].text_content()
        start_year, end_year = re.search(r"(\d{4}).+(\d{4})", date_span).groups()
        # TODO: build year_changed boolean to handle when not start_year == end_year

        table_rows = self.root.xpath(".//tbody//tr")
        agenda_items_list = []

        for row_item in table_rows:
            item_text_list = row_item.text_content().strip().split("\n")
            item_list = [x.strip() for x in item_text_list if len(x.strip()) > 0]

            # TODO: add conditions to handle blank fields in table
            #   (try empty strings?)
            bill, part_date, com, loc, descr = item_list

            # TODO: conditions to handle when bill listed as "Committee Work"
            #   or "Committee Work ####" on the schedule
            #   (in former case: leave bill_name as empty string or None,
            #   in latter case: may need to scrape chamber from next source/bill_link)

            date_time_parts = part_date.split()
            month = int(re.search(r"\d+", date_time_parts[0]).group())
            if month == 1 and not start_year == end_year:
                event_year = end_year
            else:
                event_year = start_year
            date_time_parts[0] = date_time_parts[0] + f"/{event_year}"
            date_time = " ".join(date_time_parts)

            agenda_item = {
                "bill_name": bill,
                "date_time": date_time,
                "committee": com,
                "location": loc,
                "description": descr,
            }

            agenda_items_list.append(agenda_item)

        events = EventConsolidator(agenda_items_list)
        return events.consolidate()


class NewNDEventScraper(Scraper):
    @staticmethod
    def scrape(session=None):
        # Event object needs name, start_date, and location_name
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        # event_list = EventList()
        event_list = EventsTable()
        yield from event_list.do_scrape()
