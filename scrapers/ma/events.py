import pytz
import lxml
import dateutil.parser
import datetime
import re

from utils import LXMLMixin
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


class MAEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("US/Eastern")
    date_format = "%m/%d/%Y"
    verify = False
    non_session_count = 0

    def scrape(self, chamber=None, start=None, end=None):
        if start is None:
            start_date = datetime.datetime.now().strftime(self.date_format)
        else:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
            start_date = start_date.strftime(self.date_format)

        # default to 30 days if no end
        if end is None:
            dtdelta = datetime.timedelta(days=30)
            end_date = datetime.datetime.now() + dtdelta
            end_date = end_date.strftime(self.date_format)
        else:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
            end_date = end_date.strftime(self.date_format)

        url = "https://malegislature.gov/Events/FilterEventResults"

        params = {
            "EventType": "",
            "Branch": "",
            "EventRangeType": "",
            "StartDate": start_date,
            "EndDate": end_date,
            "X-Requested-With": "XMLHttpRequest",
        }

        page = self.post(url, params, verify=False)
        page = lxml.html.fromstring(page.content)
        page.make_links_absolute("https://malegislature.gov/")

        rows = page.xpath("//table[contains(@class,'eventTable')]/tbody/tr")

        for row in rows:
            # Some rows have an additional TD at the start,
            # so index em all as offsets
            td_ct = len(row.xpath("td"))

            # Skip meetings of the chamber
            event_type = row.xpath("string(td[{}])".format(td_ct - 3))
            if event_type == "Session":
                continue

            url = row.xpath("td[{}]/a/@href".format(td_ct - 2))[0]
            yield from self.scrape_event_page(url, event_type)

        if self.non_session_count == 0:
            raise EmptyScrape

    def scrape_event_page(self, url, event_type):
        page = self.lxmlize(url)
        page.make_links_absolute("https://malegislature.gov/")

        title = page.xpath('string(//div[contains(@class,"followable")]/h1)')
        title = title.replace("Hearing Details", "").strip()
        title = title.replace("Special Event Details", "")

        start_day = page.xpath(
            '//dl[contains(@class,"eventInformation")]/dd[2]/text()[last()]'
        )[0].strip()
        start_time = page.xpath(
            'string(//dl[contains(@class,"eventInformation")]/dd[3])'
        ).strip()

        # If an event gets moved, ignore the original time
        start_time = re.sub(
            r"Original Start Time(.*)New Start Time(\n*)",
            "",
            start_time,
            flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        location = page.xpath(
            'string(//dl[contains(@class,"eventInformation")]/dd[4]//a)'
        ).strip()

        if location == "":
            location = page.xpath(
                'string(//dl[contains(@class,"eventInformation")]/dd[4])'
            ).strip()

        description = page.xpath(
            'string(//dl[contains(@class,"eventInformation")]/dd[5])'
        ).strip()

        start_date = self._TZ.localize(
            dateutil.parser.parse("{} {}".format(start_day, start_time))
        )

        event = Event(
            start_date=start_date,
            name=title,
            location_name=location,
            description=description,
        )

        event.add_source(url)

        agenda_rows = page.xpath(
            '//div[contains(@class,"col-sm-8") and .//h2[contains(@class,"agendaHeader")]]'
            '/div/div/div[contains(@class,"panel-default")]'
        )

        for row in agenda_rows:
            # only select the text node, not the spans
            agenda_title = row.xpath(
                "string(.//h4/a/text()[normalize-space()])"
            ).strip()

            if agenda_title == "":
                agenda_title = row.xpath(
                    "string(.//h4/text()[normalize-space()])"
                ).strip()

            agenda = event.add_agenda_item(description=agenda_title)

            bills = row.xpath(".//tbody/tr/td[1]/a/text()")
            for bill in bills:
                bill = bill.strip().replace(".", " ")
                agenda.add_bill(bill)

        if event_type == "Hearing":
            event.add_participant(title, type="committee", note="host")

        self.non_session_count += 1
        yield event
