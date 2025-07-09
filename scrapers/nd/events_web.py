import re
import logging
import requests
import typing
import lxml.html
from spatula import HtmlPage
from openstates.scrape import Scraper
from openstates.exceptions import EmptyScrape
from .utils import EventConsolidator


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

    def process_page(self) -> typing.Any:
        pass


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
