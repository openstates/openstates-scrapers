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
    date_format = "%Y-%m-%d"

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
        # senate website needs start_date and end_date
        upper_start_url = f"https://www.senate.ca.gov/calendar?startDate={start}&endDate={end}&committeeHearings=1"
        html = requests.get(upper_start_url).text
        page = lxml.html.fromstring(html)
        for date_row in page.xpath(
            '//div[@class="page-events--day-wrapper"]//div[contains(@class, "committee-hearings")]//div[@class="page-events__content"]'
        ):
            hearing_date = date_row.xpath(
                './../../../h2[@class="page-events__date"]/text()'
            )[0].strip()
            hearing_title = date_row.xpath(
                './/h4[contains(@class, "page-events__title")]//text()'
            )[0]
            panel_content = date_row.xpath(
                './/div[contains(@class, "page-events__chair")]/p/text()'
            )[0]
            members = [
                panel_content.split(", Chair")[0]
                .replace("SENATOR", "")
                .replace("ASSEMBLY", "")
                .replace("MEMBER", "")
                .strip()
            ]
            time_content = date_row.xpath(
                './/div[contains(@class, "page-events__time-location")]//p/text()'
            )[0]
            time_loc = [
                row
                for row in time_content.split(" - ")
                if "p.m." in row or "a.m." in row
            ]
            time_loc = "".join(time_loc)

            time_loc_parts = time_loc.split(" or ")
            hearing_time = time_loc_parts[0]
            hearing_time = (
                hearing_time.replace(".", "").strip() if ".m." in hearing_time else ""
            )
            hearing_location = time_content.split(" - ")[1]
            hearing_location = hearing_location.strip()
            when = (
                " ".join([hearing_date, hearing_time])
                .split("or")[0]
                .split("and")[0]
                .strip()
            )
            when = dateutil.parser.parse(when)
            when = self._tz.localize(when)

            # Event stgatus
            status = "confirmed"
            if "CANCEL" in panel_content:
                # Sometimes status in description
                status = "cancelled"
            # Sometimes an event has a status indicator, which is outside the "content" container / date_row
            event_status_elem = date_row.getparent().cssselect(
                "div.committee-hearing-status"
            )
            if len(event_status_elem) > 0:
                status_text = event_status_elem[0].text_content().strip().lower()
                status = (
                    "cancelled"
                    if "cancel" in status_text or "postpone" in status_text
                    else "confirmed"
                )

            event = Event(
                name=hearing_title,
                location_name=hearing_location,
                start_date=when,
                status=status,
                classification="committee-meeting",
            )

            committees = [
                f"Senate {com.strip()} Committee"
                for com in date_row.xpath(
                    './/li[@class="page-events__committee-link"]/a/text()'
                )
            ]
            for committee in committees:
                event.add_committee(committee)
            for member in members:
                event.add_person(name=member, note="chair")
            event.add_source(upper_start_url)
            view_agenda_url = (
                "https://www.senate.ca.gov"
                + date_row.xpath(
                    './following-sibling::div[@class="page-events__link-listing"]/div[@class="view-agenda-link"]/a/@href'
                )[0]
                + "&_wrapper_format=drupal_modal"
            )
            view_agenda_id = view_agenda_url.split("?")[0].split("/")[-1]
            event_key = f"{hearing_title}#{when}#{view_agenda_id}"
            event.dedupe_key = event_key
            self.scrape_upper_agenda(
                event, committees, view_agenda_url, upper_start_url
            )
            yield event

    def scrape_upper_agenda(self, event, committees, url, upper_start_url):
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.senate.ca.gov",
            "Referer": upper_start_url,
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

        data = {
            "js": "true",
            "dialogOptions[width]": "800",
            "dialogOptions[dialogClass]": "event-agenda-modal",
            "_drupal_ajax": "1",
            "ajax_page_state[theme]": "senatemigrationtheme",
            "ajax_page_state[theme_token]": "",
            "ajax_page_state[libraries]": "eJx1kFFuxCAMRC8EQuqFVg7MUisGIuwkSk9ftlH7sU1-MJr3LNDk1rLgQZXkMI4a8lvg8mqoE3oOk7Q4q98YuxP6OsLrcIpKhsK5k3Gr9omCkPCkVewaZmkTyTUrxNUX1PUaL5ThsaGaOj108DCRwu2kj0Qsx5PH5xPrInSEU_SRBDVRv7EUgmgfN3Sk_i89n_bjauh6v_E_fXMLElMQ3uDVOqiMQbaqt5ZH_T_2UKx1ndnO5s_iX2RvfdaF4m-V3zxms0E",
        }
        response = requests.post(url, headers=headers, data=data).json()
        page = lxml.html.fromstring(response[0]["data"])
        page.make_links_absolute(url)
        agenda_title = response[0]["dialogOptions"]["title"]
        agenda = event.add_agenda_item(agenda_title)

        for committee in committees:
            agenda.add_committee(committee, note="host")
        appointment_class = page.xpath(
            '//span[@class="Appointments"]/span[@class="Appointment"]'
        )
        measure_class = page.xpath(
            '//span[@class="CommitteeTopic"]//span[@class="Measure"]'
        )
        if appointment_class:
            for appointment in appointment_class:
                appointee_name = (
                    appointment.xpath('.//span[@class="AppointeeName"]/text()')[0]
                    .strip(strip_chars)
                    .replace(",", "")
                )
                appointee_position = (
                    appointment.xpath('.//span[@class="AppointedPosition"]/text()')[0]
                    .strip(strip_chars)
                    .replace(",", "")
                    .lower()
                )
                agenda.add_person(appointee_name, note=appointee_position)

        elif measure_class:
            for measure in measure_class:

                bill_id = (
                    measure.xpath('.//span[@class="MeasureType"]/text()')[0]
                    .replace("No", "")
                    .replace(".", "")
                    .replace(" ", "")
                    .strip()
                )
                note = measure.xpath('.//span[contains(@class, "Topic")]//text()')[
                    0
                ].strip()
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
                members = [item for sublist in members for item in sublist.split(", ")]

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
                    .split(" to ")[0]
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
