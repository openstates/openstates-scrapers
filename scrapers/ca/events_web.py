import datetime
import pytz
import re
import dateutil.parser
import lxml.html
from utils import LXMLMixin
from openstates.scrape import Scraper, Event
import requests


strip_chars = ".,\t\n\r "


class CAEventWebScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Pacific")
    date_format = "%m-%d-%Y"

    def scrape(self, chamber=None, start=None, end=None):
        if start is None:
            start_date = datetime.datetime.now()
            start_date = start_date.strftime(self.date_format)
        else:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
            start_date = start_date.strftime(self.date_format)

        # default to 60 days if no end
        if end is None:
            dtdelta = datetime.timedelta(days=60)
            end_date = datetime.datetime.now() + dtdelta
            end_date = end_date.strftime(self.date_format)
        else:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
            end_date = end_date.strftime(self.date_format)

        if chamber in ["upper", None]:
            for event in self.scrape_upper(start_date, end_date):
                yield event

        if chamber in ["lower", None]:
            for event in self.scrape_lower():
                yield event

    def scrape_upper(self, start, end):
        # https://www.senate.ca.gov/calendar?startdate=01-17-2024&
        # enddate=01-24-2024&committee=&committee-hearings=on
        # senate website needs start_date and end_date
        # set it to a week
        upper_start_url = f"https://www.senate.ca.gov/calendar?startdate={start}&enddate={end}&committee=&committee-hearings=on"
        html = requests.get(upper_start_url).text
        page = lxml.html.fromstring(html)

        for date_row in page.xpath('//div[contains(@class, "calendarDayContainer")]'):
            hearing_date = date_row.xpath('.//div[@class="calendarDate"]/text()')[
                0
            ].strip()
            for committee_row in date_row.xpath(
                './/div[@class="eventContainer"][1]/div[@class="panel panel-default"]'
            ):
                hearing_title = committee_row.xpath(
                    './/div[@class="panel-heading"]//strong'
                )[0].xpath("string()")
                panel_content = committee_row.xpath('.//div[@class="panel-content"]')[
                    0
                ].xpath("string()")
                members = [
                    m.replace("SENATOR", "")
                    .replace("ASSEMBLY", "")
                    .replace("MEMBER", "")
                    .strip(strip_chars)
                    .title()
                    for m in panel_content.split("Chair")[0].split("AND")
                ]
                time_loc = [
                    row
                    for row in panel_content.split("\n")
                    if "p.m." in row or "a.m." in row or " - " in row
                ]
                time_loc = "".join(time_loc)

                time_loc_parts = time_loc.split(" - ")
                hearing_time = time_loc_parts[0]
                hearing_time = (
                    hearing_time.replace(".", "").strip(strip_chars)
                    if ".m." in hearing_time
                    else ""
                )
                hearing_location = " ".join(time_loc_parts[1:])
                hearing_location = hearing_location.strip(strip_chars)

                when = (
                    " ".join([hearing_date, hearing_time])
                    .split("or")[0]
                    .split("and")[0]
                    .strip()
                )
                when = dateutil.parser.parse(when)
                when = self._tz.localize(when)

                status = "cancelled" if "CANCEL" in panel_content else "confirmed"

                event = Event(
                    name=hearing_title,
                    location_name=hearing_location,
                    start_date=when,
                    status=status,
                    classification="committee-meeting",
                )

                committees = [
                    f"Senate {com.strip()} Committee"
                    for com in committee_row.xpath(
                        './/a[@class="panel-committees"]/text()'
                    )
                ]
                for member in members:
                    event.add_person(name=member, note="chair")
                event.add_source(upper_start_url)
                view_agenda_id = committee_row.xpath(
                    './/button[contains(@class, "view-agenda")]/@data-nid'
                )[0]
                event_key = f"{hearing_title}#{when}#{view_agenda_id}"
                event.dedupe_key = event_key
                view_agenda_url = f"https://www.senate.ca.gov/getagenda?dfid={view_agenda_id}&type=committee"
                self.scrape_upper_agenda(event, committees, view_agenda_url)
                yield event

    def scrape_upper_agenda(self, event, committees, url):
        response = self.get(url).json()
        page = lxml.html.fromstring(response["agenda"])
        page.make_links_absolute(url)
        start = False

        for span in page.xpath('.//span[@class="CommitteeTopic "]/span'):
            span_class = span.xpath("@class")[0].strip(strip_chars)
            span_title = span.xpath("string()").strip(strip_chars)
            span_title = re.sub(r"\s+", " ", span_title)
            span_title = re.sub(r"^\d+", "", span_title)
            span_title = span_title.replace("SUBJECT:", "").strip(strip_chars)

            if "linesep" in span_class:
                start = True
            if not start:
                continue
            if "HearingTopic " in span_class:
                continue
            if not span_title:
                continue
            agenda = event.add_agenda_item(span_title)

            for committee in committees:
                agenda.add_committee(committee, note="host")

            if "Appointment" in span_class:
                appointee_name = (
                    span.xpath('.//span[@class="AppointeeName"]')[0]
                    .xpath("string()")
                    .strip(strip_chars)
                )
                appointee_position = (
                    span.xpath('.//span[@class="AppointedPosition"]')[0]
                    .xpath("string()")
                    .strip(strip_chars)
                    .lower()
                )
                agenda.add_person(appointee_name, note=appointee_position)

            elif "Measure row" in span_class:
                bill_id = (
                    span.xpath('.//a[contains(@class, "MeasureLink")]')[0]
                    .xpath("string()")
                    .replace("No", "")
                    .replace(".", "")
                    .replace(" ", "")
                    .strip(strip_chars)
                )
                note = (
                    " ".join(span.xpath('.//span[contains(@class, "Topic")]//text()'))
                    .strip(strip_chars)
                    .strip(strip_chars)
                )
                agenda.add_bill(bill_id, note=note)

    def scrape_lower(self):
        lower_start_url = (
            "https://www.assembly.ca.gov/schedules-publications/assembly-daily-file"
        )
        html = requests.get(lower_start_url).text
        page = lxml.html.fromstring(html)

        for date_row in page.xpath("//h5[@class='date']"):
            hearing_date = date_row.xpath("string()").strip()

            for content_xpath in date_row.xpath(
                './following-sibling::div[@class="wrapper--border"][1]/div[@class="dailyfile-section-item"]'
            ):
                hearing_title = (
                    content_xpath.xpath('.//div[@class="hearing-name"]')[0]
                    .xpath("string()")
                    .strip()
                )
                members = [
                    m.replace("SENATOR", "")
                    .replace("ASSEMBLY", "")
                    .replace("MEMBER", "")
                    .strip(strip_chars)
                    .title()
                    for m in content_xpath.xpath('.//div[@class="attribute chair"]')[0]
                    .xpath("string()")
                    .split(", Chair")[0]
                    .split("AND")
                ]

                time_loc = content_xpath.xpath(
                    './/div[@class="attribute time-location"]'
                )[0].xpath("string()")

                time_loc = time_loc.split(" - ")
                hearing_time = time_loc[0]
                hearing_location = " - ".join(time_loc[1:])
                hearing_time = (
                    hearing_time.replace(".", "").strip(strip_chars)
                    if ".m." in hearing_time
                    else ""
                )
                hearing_location = hearing_location.strip(strip_chars)

                when = (
                    " ".join([hearing_date, hearing_time])
                    .split("or")[0]
                    .split("and")[0]
                    .split("to")[0]
                    .strip()
                )
                when = dateutil.parser.parse(when)
                when = self._tz.localize(when)

                event = Event(
                    name=hearing_title,
                    location_name=hearing_location,
                    start_date=when,
                    classification="committee-meeting",
                )
                event_key = f"{hearing_title}#{when}#{hearing_location}"
                event.dedupe_key = event_key

                committees = [
                    f"Assembly {com.strip()} Committee"
                    for com in content_xpath.xpath(
                        './/div[@class="attribute committees"]/ul/li/a/text()'
                    )
                ]

                for member in members:
                    event.add_person(name=member, note="chair")

                event.add_source(lower_start_url)

                agenda_xpaths = content_xpath.xpath('.//div[@class="agenda"]')

                for agenda_xpath in agenda_xpaths:
                    self.scrape_lower_agenda(event, committees, agenda_xpath)

                yield event

    def scrape_lower_agenda(self, event, committees, page):
        start = False

        for span in page.xpath('.//span[@class="CommitteeTopic"]/span'):
            span_class = span.xpath("@class")[0].strip(strip_chars)
            span_title = (" ".join(span.xpath(".//text()"))).strip(strip_chars)
            span_title = re.sub(r"\s+", " ", span_title)
            span_title = re.sub(r"^\d+", "", span_title)
            span_title = span_title.replace("SUBJECT:", "").strip(strip_chars)

            if "linesp" in span_class or "HearingTopic" in span_class:
                start = True
            if not start:
                continue
            if "HearingTopic" in span_class or "Header" in span_class:
                continue

            if span_title:
                agenda = event.add_agenda_item(span_title)
                for committee in committees:
                    agenda.add_committee(committee, note="host")

            if "Measure" == span_class:
                bill_id = (
                    span.xpath(".//a")[0]
                    .xpath("string()")
                    .replace("No", "")
                    .replace(".", "")
                    .replace(" ", "")
                    .strip(strip_chars)
                )
                note = " ".join(
                    span.xpath('.//span[contains(@class, "Topic")]//text()')
                ).strip(strip_chars)
                agenda.add_bill(bill_id, note=note)
