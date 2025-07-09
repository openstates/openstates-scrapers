import csv
import pytz
import re

from openstates.scrape import Scraper
from .utils import EventConsolidator

tz = pytz.timezone("US/Central")


class NDEventsCSVScraper(Scraper):
    def scrape(self):

        events_csv_url = "https://www.ndlegis.gov/legend/committee/hearings/public-schedule/?export=csv"
        events_csv_response = self.get(events_csv_url)
        events_csv_reader = csv.DictReader(
            events_csv_response.iter_lines(decode_unicode=True)
        )

        agenda_items_list = []
        for event_csv_row in events_csv_reader:
            part_date = event_csv_row["Hearing Date/Time"].strip()
            bill_col = event_csv_row["Bill"].strip()
            agenda_time = event_csv_row["Agenda Time"].strip()
            com = event_csv_row["Committee"].strip()
            sub_com = event_csv_row["Subcommittee"].strip()
            loc = event_csv_row["Room"].strip()
            descr = event_csv_row["Description"].strip()

            # Example Column:
            #   bill      part_date          com      sub_com  loc       descr
            # HB 1111 | 12/08 2:00 PM | Joint Approps |      | 327E | Funding bill

            bill_name = ""
            full_bill_name_match = re.search(r"[A-Z]{1,4}\s+\d+", bill_col)
            if full_bill_name_match:
                bill_name = full_bill_name_match.group()
            else:
                partial_bill_name_match = re.search(r"\d+", bill_col)
                if partial_bill_name_match:
                    match_in_descr = re.search(r"[A-Z]{1,4}\s{0,3}\d+", descr)
                    if match_in_descr:
                        bill_name = match_in_descr.group()

            date_fixed_ampm = part_date.replace(":AM", "AM").replace(":PM", "PM")

            agenda_item = {
                "bill_name": bill_name,
                "date_time": date_fixed_ampm,
                "agenda_time": agenda_time,
                "committee": com,
                "sub_com": sub_com,
                "location": loc,
                "description": descr,
            }

            agenda_items_list.append(agenda_item)

        events = EventConsolidator(agenda_items_list, events_csv_url)
        yield from events.consolidate()
