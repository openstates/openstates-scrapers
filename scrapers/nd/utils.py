import dateutil.parser
import logging
import pytz
import re

from openstates.scrape import Event


def time_is_earlier(new, current):
    new_magnitude = int(new[0:2] + new[3:5])
    current_magnitude = int(current[0:2] + current[3:5])
    if new_magnitude < current_magnitude:
        return True
    else:
        return False


class EventConsolidator(object):
    def __init__(self, items, url):
        self.items = items
        self.events = {}
        self._tz = pytz.timezone("US/Central")
        self.url = url
        logging.getLogger("scrapelib").setLevel(logging.WARNING)

    def consolidate(self):
        for item in self.items:
            date_time = item["date_time"]
            local_date = dateutil.parser.parse(date_time)

            item_date, item_time = str(local_date).split()
            agenda_time = item["agenda_time"]
            bill_name = item["bill_name"]
            item_id = f"{item_time}+{bill_name}"

            committee = item["committee"]
            location = item["location"]
            event_key = f"{item_date}-{committee}-{location}"

            if not self.events.get(event_key, None):
                self.events[event_key] = {
                    "event_start_time": item_time,
                    "item_keys": set(),
                }
            else:
                current_start = self.events[event_key]["event_start_time"]
                if time_is_earlier(item_time, current_start):
                    self.events[event_key]["event_start_time"] = item_time

            self.events[event_key]["item_keys"].add(item_id)

            agenda_item_details = {
                "description": item["description"],
                "bill_name": item["bill_name"],
                "agenda_time": agenda_time,
                "sub_com": item["sub_com"],
            }
            self.events[event_key][item_id] = agenda_item_details

        yield from self.create_events()

    def create_events(self):
        event_names = set()
        for event in self.events.keys():
            date, com, loc = re.search(r"(.+)\-(.+)\-(.+)", event).groups()
            date = "".join(c for c in date if c.isdigit() or c in ["-"])

            start_time = self.events[event]["event_start_time"]
            date_time = f"{date} {start_time}"
            date_object = dateutil.parser.parse(date_time)
            date_with_offset = self._tz.localize(date_object)
            event_name = f"{com}#{loc}#{date_time}"
            if event_name in event_names:
                logging.warning(f"Skipping duplicate event {event_name}")
                continue
            event_names.add(event_name)
            event_obj = Event(
                name=com,
                location_name=loc,
                description="Standing Committee Hearing",
                start_date=date_with_offset,
            )
            event_obj.add_committee(com)
            event_obj.dedupe_key = event_name

            for item_key in self.events[event]["item_keys"]:
                item = self.events[event][item_key]
                agenda_time = item["agenda_time"]
                descr_with_time = f"[{agenda_time}]: {item['description']}"
                item_descr = event_obj.add_agenda_item(descr_with_time)
                if item["bill_name"]:
                    item_descr.add_bill(item["bill_name"])
                if item["sub_com"]:
                    item_descr["extras"]["sub_committee"] = item["sub_com"]

            event_obj.add_source(self.url)

            yield event_obj
