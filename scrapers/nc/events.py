import dateutil.parser
from dateutil.parser import ParserError
import datetime
import pytz
import re
import requests
import lxml.html
from openstates.scrape import Scraper, Event
from utils import LXMLMixin
from utils.events import match_coordinates
from openstates.exceptions import EmptyScrape


class UnknownBillIdFormatError(BaseException):
    def __init__(self, raw_bill_id):
        super().__init__(f"Unexpected format: '{raw_bill_id}'")


class UnknownBillIdPrefixError(BaseException):
    def __init__(self, prefix):
        super().__init__(f"Unexpected prefix: '{prefix}'")


class NCEventScraper(Scraper, LXMLMixin):
    verify = False
    _tz = pytz.timezone("US/Eastern")
    bill_id_re = re.compile(r"([A-Z]\w+\s)*([A-Z]\w+\s)([A-Z]\w+\s)(\d+)")

    def scrape(self):
        url = "https://www.ncleg.gov/LegislativeCalendar/"
        page = self.lxmlize(url)
        page.make_links_absolute(url)
        event_count = 0
        for day_row in page.xpath('//div[@class="row cal-event-day"]'):

            date = day_row.xpath(
                './/div[contains(@class, "cal-event-day-full")]/text()'
            )[0].strip()
            for row in day_row.xpath('.//div[contains(@class, "cal-event row")]'):
                status = "tentative"
                # first cal-event-row sometimes contains full date, skip that
                time = row.xpath(
                    'div[contains(@class,"col-12 text-left col-sm-3 text-sm-right")]/text()'
                )[0].strip()

                event_row = row.xpath(
                    'div[contains(@class,"col-12 col-sm-9 col-md-12 ")]'
                )[0]

                # skip floor sessions
                if event_row.xpath('.//a[contains(text(), "Session Convenes")]'):
                    continue

                chamber = ""
                if len(
                    event_row.xpath(
                        'span[contains(@class, "text-dark font-weight-bold")]/text()'
                    )
                ):
                    chamber = event_row.xpath(
                        'span[contains(@class, "text-dark font-weight-bold")]/text()'
                    )[0].strip()
                    chamber = chamber.replace(":", "")

                # sometimes there are unlinked events, usually just press conferences
                if not event_row.xpath('a[contains(@href,"/Committees/")]'):
                    continue

                com_link = event_row.xpath('a[contains(@href,"/Committees/")]')[0]
                com_name = com_link.text_content().strip()
                com_name = f"{chamber} {com_name}".strip()

                com_url = com_link.xpath("@href")[0]

                where = (
                    row.xpath('div[contains(@class,"col-12 offset-sm-3")]')[0]
                    .text_content()
                    .strip()
                )
                where = where.replace("STREAM", "")

                when = f"{date} {time}"
                try:
                    when = dateutil.parser.parse(when)
                    # occasionally they'd do 9am-1pm which confuses the TZ detection
                    when = self._tz.localize(when)
                except (ParserError, ValueError):
                    self.warning(f"Unable to parse {time}, only using day component")
                    when = dateutil.parser.parse(date)
                    when = self._tz.localize(when).date()

                if when < self._tz.localize(datetime.datetime.now()):
                    status = "passed"

                if "canceled" in com_name.lower() or "cancelled" in com_name.lower():
                    status = "cancelled"

                if "LOB" in where:
                    where = f"16 W Jones St, Raleigh, NC 27601, {where}"

                com_name = self.clean_name(com_name)
                event = Event(
                    name=com_name,
                    start_date=when,
                    location_name=where,
                    classification="committee-meeting",
                    status=status,
                )
                event.add_source(com_url)

                event.add_participant(com_name, type="committee", note="host")

                # NOTE: if you follow the committee link, there are agenda PDF links
                # but they don't load at all as of 2021-02-01 -- showerst

                for agenda_row in event_row.xpath(".//p"):
                    agenda_text = agenda_row.text_content().strip()
                    if agenda_text != "":
                        agenda = event.add_agenda_item(agenda_text)

                        for bill_row in agenda_row.xpath(
                            './/a[contains(@href,"BillLookUp")]'
                        ):
                            # Make request to BillLookUp page to scrape proper
                            #  bill_id, because event list page only lists
                            #  bills/resolutions in format 'S123' or 'H456',
                            #  but proper prefixes are one of the following:
                            #  {'SJR', 'HB', 'HR', 'SB', 'HJR', 'SR'}
                            bill_url = bill_row.get("href")
                            bill_resp = requests.get(bill_url)
                            bill_page = lxml.html.fromstring(bill_resp.content)
                            raw_bill_id = bill_page.xpath(
                                ".//div[@class='col-12 col-sm-6 h2 text-center order-sm-2']/text()"
                            )[0]
                            bill_id = self.clean_bill_id(raw_bill_id)
                            agenda.add_bill(bill_id)

                if row.xpath(".//a[@title='Stream meeting']"):
                    media_url = row.xpath(".//a[@title='Stream meeting']/@href")[0]
                    event_page = self.lxmlize(media_url)
                    if event_page.xpath("//audio"):
                        event.add_media_link("Audio", media_url, "text/html")
                    if event_page.xpath("//iframe[contains(@src,'youtube')]"):
                        event.add_media_link(
                            "Youtube",
                            event_page.xpath("//iframe[contains(@src,'youtube')]/@src")[
                                0
                            ],
                            "text/html",
                        )
                match_coordinates(event, {"16 W Jones": (35.78331, -78.63889)})
                event_count += 1
                yield event
        if event_count < 1:
            raise EmptyScrape

    def clean_name(self, name):
        return re.sub(r"[\-\-\s*]+(UPDATED|CANCELLED)", "", name).strip()

    def clean_bill_id(self, raw_bill_id):
        expected_prefixes = {"SJR", "HB", "HR", "SB", "HJR", "SR"}
        bill_id_match = self.bill_id_re.search(raw_bill_id)
        if bill_id_match:
            bill_id_full_list = [x for x in bill_id_match.groups() if x]
            prefix = "".join(x[0] for x in bill_id_full_list[:-1])
            if prefix not in expected_prefixes:
                raise UnknownBillIdPrefixError(prefix)
            bill_id = f"{prefix} {bill_id_full_list[-1]}"
            return bill_id
        else:
            raise UnknownBillIdFormatError(raw_bill_id)
