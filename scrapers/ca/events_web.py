import datetime
import pytz
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
            time_content_parts = time_content.split(" - ")
            if len(time_content_parts) > 1:
                hearing_location = time_content_parts[1]
            else:
                hearing_location = time_content_parts[0]
            hearing_location = hearing_location.strip()
            when = (
                " ".join([hearing_date, hearing_time])
                .split("or")[0]
                .split("and")[0]
                .strip()
            )
            when = dateutil.parser.parse(when, fuzzy=True)
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

                bill_type = (
                    measure.xpath('.//span[@class="MeasureType"]/text()')[0]
                    .replace(".", "")
                    .strip()
                )
                bill_number = measure.xpath('.//span[@class="MeasureNum"]/text()')[
                    0
                ].strip()
                bill_id = f"{bill_type}{bill_number}"
                note = measure.xpath('.//span[contains(@class, "Topic")]//text()')[
                    0
                ].strip()
                agenda.add_bill(bill_id, note=note)

    def scrape_lower(self):
        lower_start_url = (
            "https://www.assembly.ca.gov/schedules-publications/daily-file"
        )
        html = requests.get(lower_start_url).text
        page = lxml.html.fromstring(html)

        for date_row in page.xpath(
            "//table[contains(@class, 'committee-hearing-table')]/tbody/tr"
        ):
            hearing_topic = hearing_subject = None

            # Get event basics
            hearing_date = date_row.xpath("td[@class='committee_hearing-date']/text()")[
                0
            ].strip()
            hearing_time = (
                date_row.xpath("td[@class='committee_hearing-time']/text()")[0]
                .lower()
                .strip()
            )
            committee_name = date_row.xpath(
                "td[@class='committee_hearing-name']/text()"
            )[0].strip()
            hearing_location = date_row.xpath(
                "td[@class='committee_hearing-location']/text()"
            )[0].strip()

            # Parse date/time
            if " to " in hearing_time.lower():
                # remove the " to 12 noon" in something like "9:30am to 12 noon"
                hearing_time = hearing_time.lower().split(" to ")[0]
            if "am" in hearing_time or "pm" in hearing_time:
                when = f"{hearing_date} {hearing_time}"
                when = dateutil.parser.parse(when)
                when = self._tz.localize(when)
                all_day = False
            else:
                when = dateutil.parser.parse(hearing_date)
                when = self._tz.localize(when)
                all_day = True

            # If agenda URL, fetch and parse
            bill_numbers = []
            agenda_url = None
            agenda_urls = date_row.xpath(
                "td[@class='committee_hearing-menu']//a[@class='use-ajax']/@href"
            )
            if len(agenda_urls) > 0:
                agenda_url = f"https://www.assembly.ca.gov{agenda_urls[0]}"
                agenda_html = requests.get(agenda_url).text
                agenda_page = lxml.html.fromstring(agenda_html)

                # topic examples: INFORMATIONAL HEARING, OVERSIGHT HEARING, FOR CONCURRENCE VOTE PER A.R. 77.2
                # sometimes there is more than one topic, ex: https://www.assembly.ca.gov/api/dailyfile/agenda/18616
                hearing_topics = agenda_page.xpath(
                    "//span[@class='HearingTopic']/text()"
                )
                if len(hearing_topics) > 0:
                    hearing_topic = hearing_topics[0].strip()

                # subject examples:
                # Infrastructure, Pollution, and Climate Resilience
                # 50th Annual Zeke Grader Fisheries Forum
                # The Future of Higher Education and the Role of the Federal Government.
                hearing_subjects = agenda_page.xpath(
                    "//span[@class='HearingSubject']/text()"
                )
                if len(hearing_subjects) > 0:
                    hearing_subject = hearing_subjects[0].strip()

                # Bills
                # ex with bills: https://www.assembly.ca.gov/api/dailyfile/agenda/18616
                bill_links = agenda_page.xpath("//span[@class='Measure']//a")
                if len(bill_links) > 0:
                    for bill_link in bill_links:
                        bill_number_raw = bill_link.text_content().strip()
                        bill_number = (
                            bill_number_raw.replace(".", "").replace("No", "").strip()
                        )
                        bill_numbers.append(bill_number)

            # Create event
            event = Event(
                name=committee_name,
                location_name=hearing_location,
                start_date=when,
                classification="committee-meeting",
                all_day=all_day,
            )
            event_key = f"{committee_name}#{when}#{hearing_location}"
            event.dedupe_key = event_key
            event.add_source(lower_start_url)
            if agenda_url:
                event.add_source(agenda_url)

            if hearing_subject:
                agenda_title = hearing_subject
            elif hearing_topic:
                agenda_title = hearing_topic
            else:
                agenda_title = committee_name
            agenda = event.add_agenda_item(agenda_title)
            agenda.add_committee(committee_name, note="host")
            for bill_number in bill_numbers:
                agenda.add_bill(bill_number)

            yield event
