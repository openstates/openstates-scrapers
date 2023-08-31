import re
import pytz
import logging
import dateutil.parser
import requests
import lxml.html
from spatula import HtmlPage
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


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


class BillNameScraper(HtmlPage):
    def __init__(self, source):
        self.source = source

    def get_bill_name(self):
        response = requests.get(self.source)
        content = lxml.html.fromstring(response.content)
        try:
            bill_name_tag = content.xpath(".//div[@id='content']//h3")[0]
            bill_name = bill_name_tag.text_content().strip()
            return bill_name
        except Exception:
            return ""


class EventsTable(HtmlPage):
    events_path = "/legend/committee/hearings/public-schedule/"
    source = f"https://www.ndlegis.gov{events_path}"

    def process_page(self):
        date_span = self.root.xpath(".//h5[2]")[0].text_content()
        start_year, end_year = re.search(r"(\d{4}).+(\d{4})", date_span).groups()

        table_rows = self.root.xpath(".//tbody//tr")
        agenda_items_list = []

        for row_item in table_rows:
            columns = row_item.xpath("./td")
            columns_content = [x.text_content().strip() for x in columns]
            if len(columns_content) > 7:
                columns_content = columns_content[:7]
            part_date, bill, agenda_time, com, sub_com, loc, descr = columns_content
            # Example Column:
            #   bill      part_date          com      sub_com  loc       descr
            # HB 1111 | 12/08 2:00 PM | Joint Approps |      | 327E | Funding bill

            full_bill_name_match = re.search(r"[A-Z]{1,4}\s+\d+", bill)
            if full_bill_name_match:
                bill_name = full_bill_name_match.group()
            else:
                partial_bill_name_match = re.search(r"\d+", bill)
                if partial_bill_name_match:
                    match_in_descr = re.search(r"[A-Z]{1,4}\s{0,3}\d+", descr)
                    if match_in_descr:
                        bill_name = match_in_descr.group()
                    else:
                        bill_link = columns[1].xpath("./a")[0].get("href")
                        bill_name_scraper = BillNameScraper(bill_link)
                        bill_name = bill_name_scraper.get_bill_name()
                else:
                    bill_name = ""

            date_time_parts = part_date.split()
            month = int(re.search(r"\d+", date_time_parts[0]).group())
            if month == 1 and not start_year == end_year:
                event_year = end_year
            else:
                event_year = start_year
            date_time_parts[0] += f"/{event_year}"
            date_time = " ".join(date_time_parts)

            agenda_item = {
                "bill_name": bill_name,
                "date_time": date_time,
                "agenda_time": agenda_time,
                "committee": com,
                "sub_com": sub_com,
                "location": loc,
                "description": descr,
            }

            agenda_items_list.append(agenda_item)

        events = EventConsolidator(agenda_items_list, self.source.url)
        yield from events.consolidate()


class NDEventScraper(Scraper):
    @staticmethod
    def scrape():
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        event_list = EventsTable()
        event_count = 0
        for event in event_list.do_scrape():
            event_count += 1
            yield event
        if event_count < 1:
            raise EmptyScrape
