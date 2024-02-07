import datetime
import dateutil.parser
import lxml
import pytz

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape
from utils import LXMLMixin


class MAEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("US/Eastern")
    date_format = "%m/%d/%Y"
    verify = False
    non_session_count = 0

    def scrape(self, chamber=None, start=None, end=None):
        dtdelta = datetime.timedelta(days=30)

        if start is None:
            start_date = datetime.datetime.now() - dtdelta
        else:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
        start_date = start_date.strftime(self.date_format)

        # default to 30 days if no end
        if end is None:
            end_date = datetime.datetime.now() + dtdelta
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

        title = page.xpath('string(//div[contains(@class,"followable")]/h1)').strip()
        sub_title = page.xpath(
            'string(//div[contains(@class,"followable")]/h1/span)'
        ).strip()
        title = title.replace(sub_title, "")

        status = (
            page.xpath('string(//dt[contains(., "Status:")]/following-sibling::dd[1])')
            .lower()
            .strip()
        )
        if "cancel" in status:
            status = "cancelled"
        elif "complete" in status:
            status = "passed"
        elif "confirm" in status:
            status = "confirmed"
        elif "reschedule" in status:
            status = "confirmed"
        else:
            status = "tentative"

        start_day = (
            page.xpath(
                'string(//dt[contains(., "Event Date:")]/following-sibling::dd[1])'
            )
            .split("New Start Date")[-1]
            .strip()
        )
        start_time = (
            page.xpath(
                'string(//dt[contains(., "Start Time:")]/following-sibling::dd[1])'
            )
            .split("New Start Time")[-1]
            .strip()
        )

        location = (
            page.xpath(
                'string(//dt[contains(., "Location:")]/following-sibling::dd[1])'
            )
            .split("New Location")[-1]
            .strip()
        )
        location = " ".join(location.split())

        description = (
            page.xpath(
                'string(//dt[contains(., "Event Description")]/following-sibling::dd[1])'
            )
            .split("\n")[0]
            .strip()
        )
        description = " ".join(description.split())

        start_date = self._TZ.localize(
            dateutil.parser.parse("{} {}".format(start_day, start_time))
        )

        event = Event(
            start_date=start_date,
            name=title,
            location_name=location,
            description=description,
            status=status,
        )

        event.add_source(url)

        agenda_rows = page.xpath(
            '//div[@id="agendaSection"]//div[contains(@class,"panel-default")]'
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
                bill = bill.strip().replace(".", "")
                agenda.add_bill(bill)

        event.add_participant(title, type="committee", note="host")

        video_srcs = page.xpath("//video/source")
        if video_srcs:
            for video_src in video_srcs:
                video_url = video_src.xpath("@src")[0].strip()
                video_mime = video_src.xpath("@type")[0]
                event.add_media_link("Hearing Video", video_url, video_mime)

        self.non_session_count += 1
        yield event
