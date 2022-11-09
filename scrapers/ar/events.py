import re
import datetime
import dateutil.parser
import lxml
import pytz
from openstates.scrape import Scraper, Event
from utils.events import match_coordinates


# usage:
#  PYTHONPATH=scrapers poetry run os-update va events --scrape start=YYYY-mm-dd end=YYYY-mm-dd
class AREventScraper(Scraper):
    _tz = pytz.timezone("America/Chicago")
    date_format = "%Y-%m-%d"

    def scrape(self, start=None, end=None):
        if start is None:
            start_date = datetime.datetime.now().strftime(self.date_format)

        # default to 90 days if no end
        if end is None:
            dtdelta = datetime.timedelta(days=90)
            end_date = datetime.datetime.now() + dtdelta
            end_date = end_date.strftime(self.date_format)

        url = f"https://www.arkleg.state.ar.us/Calendars/Meetings?tbType=&meetingStartDate={start_date}&meetingEndDate={end_date}"

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath(
            "//div[@id='meetingBodyWrapper']/div[contains(@class,'row')]"
        ):
            row_class = row.xpath("@class")[0]
            if "tableSectionHeader" in row_class:
                day = row.xpath("div/text()")[0].strip()
                continue

            time = row.xpath("div[contains(@class,'timeRow')]/b/text()")[0].strip()
            if "no meeting" in time.lower() or "cancelled" in time.lower():
                continue

            if "upon adjournment" in time.lower():
                time = "1:00 PM"

            title = row.xpath("div[2]/b")[0].text_content().strip()

            if "call of the chair" in time.lower():
                time = ""
            elif re.findall(r"\d+:\d+\s*[A|P]M", time):
                times = re.findall(r"\d+:\d+\s*[A|P]M", time)
                time = times[0]
            else:
                self.warning(f"Unable to determine time for {time}, skipping")
                continue

            when = dateutil.parser.parse(f"{day} {time}")
            when = self._tz.localize(when)

            location = row.xpath("div[2]/text()")[1].strip()

            if location == "":
                self.warning(f"Skipping {title} due to no location")
                continue

            if re.match(r"(.*)MAC\s*$", location):
                location = re.sub(
                    "MAC",
                    "Arkansas Multi-Agency Complex, 1 Capitol Mall, Little Rock, AR 72201",
                    location,
                )
            elif re.match(r"^Room\s.*$", location, flags=re.IGNORECASE) or re.match(
                "^(House|Senate) Chamber", location, flags=re.IGNORECASE
            ):
                location = f"{location}, Arkansas State Capitol, 500 Woodlane St, Little Rock, AR 72201"

            event = Event(
                name=title,
                start_date=when,
                location_name=location,
                description="",
            )
            event.add_source("https://www.arkleg.state.ar.us/Calendars/Meetings")

            if row.xpath(".//a[@aria-label='Agenda']"):
                agenda_url = row.xpath(".//a[@aria-label='Agenda']/@href")[0]
                event.add_document("Agenda", agenda_url, media_type="application/pdf")

            if row.xpath(".//a[@aria-label='Play Video']"):
                video_url = row.xpath(".//a[@aria-label='Play Video']/@href")[0]
                event.add_media_link(
                    "Video of Hearing", video_url, media_type="text/html"
                )

            if row.xpath(".//a[@aria-label='Referred']"):
                bill_url = row.xpath(".//a[@aria-label='Referred']/@href")[0]
                self.scrape_referred_bills(event, bill_url)

            match_coordinates(
                event,
                [
                    ("1 capitol mall", ("34.74710754332397", "-92.290421823471")),
                    ("500 woodlane", ("34.74640441284063", "-92.2895327976071")),
                ],
            )

            yield event

    def scrape_referred_bills(self, event, url):
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        if page.xpath("//div[contains(@class,'billSubtitle')]"):
            agenda = event.add_agenda_item("Referred Bills")

            for row in page.xpath("//div[contains(@class,'measureTitle')]/a/text()"):
                agenda.add_bill(row.strip())
