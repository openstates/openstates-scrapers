import pytz
import datetime

from utils import LXMLMixin
from utils.media import get_media_type
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape
from spatula import HtmlPage, PdfPage, URL, XPath, SelectorError
import scrapelib
import requests
import re

bills_re = re.compile(
    r"(SJR|AR|AJR|IP|SCR|SB|ACR|SR|AB)\s{0,5}0*(\d+)", flags=re.IGNORECASE
)

date_re = re.compile(r"([a-z]+ \d{1,2}, .* (am|pm))", flags=re.IGNORECASE)

start_time_re = re.compile(r"Start\s*Time\s*(\d+)\s*(AM|PM)", flags=re.IGNORECASE)


class AgendaStartTime(PdfPage):
    def process_page(self):
        # Simplify text to make regex simpler
        text = self.text.replace(". ", "").replace(".", "")

        start = start_time_re.search(text)
        if not start:
            # Default to 12am if no start time is found
            return "12:00 AM"
        time, am_pm = start.groups(1)
        return f"{time}:00 {am_pm}"


class Agenda(PdfPage):
    def process_page(self):
        # Simplify text to make regex simpler
        text = self.text.replace(". ", "").replace(".", "")

        # Find all bill ids
        bills = bills_re.findall(text)

        # Format bills before yielding
        formatted_bills = set()
        for alpha, num in bills:
            formatted_bills.add(f"{alpha.upper()} {num}")

        yield from formatted_bills


class Meetings(HtmlPage):
    source = "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Meetings"

    def process_page(self):
        # Use session selector dropdown menu to find latest session
        session_id = (
            XPath('//div[@aria-labelledby="session"]/a[1]/@href')
            .match_one(self.root)
            .rsplit("/", 1)[1]
        )

        session_link = URL(
            url=f"https://www.leg.state.nv.us/App/NELIS/REL/{session_id}/Meetings?Meetings=System.Collections.Generic.List%601%5BNvLeg.Models.Nelis.SessionManager.Views.MeetingComposite%5D&MeetingsFilters=System.DateTime%5B%5D&ShowFloorMeetings=True&ShowCommitteeMeetings=True&ShowConferenceCommittees=True",
            method="POST",
            data={
                "MeetingsFilters": [
                    "1/1/2000",
                    "1/1/2999",
                ],
                "ShowCommitteeMeetings": [
                    "true",
                    "false",
                ],
                "ShowFloorMeetings": "false",
                "ShowConferenceCommittees": "false",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        yield CurrentMeetings(source=session_link)


class CurrentMeetings(HtmlPage):
    _TZ = pytz.timezone("PST8PDT")
    time_in_date_re = re.compile(r"(.+\d+:\d{2}\s+)(AM|PM|A\.M\.|P\.M\.)")

    def process_page(self):
        meetings = []
        cur_row = []
        # Each meeting has info spread across up to 3 divs, with a <hr> after
        # each section - The following code finds all of these sections with 3
        # divs and places them into the meetings variable
        for i in self.root.getchildren():
            if i.tag == "div":
                cur_row.append(i)
            elif i.tag == "hr":
                # Only add if all three elements are present - missing elements
                # indicate that this section is cancelled or floor meeting
                if len(cur_row) == 3:
                    meetings.append(cur_row)
                # Reset cur_row so leftover elements don't get mixed in with next set of divs
                cur_row = []
        event_count = 0
        for i in meetings:
            # First element contains: the title and date
            title = XPath(".//h3/a[1]/text()").match_one(i[0])

            # Extract all committees involved in meeting from the title
            # Some joint meetings don't start with the joint prefix so extra logic
            # is needed to get the names of all involved committees
            add_joint_prefix = False
            joint_prefix = "Joint Meeting of the "
            separator = "%$%$%"
            if title.startswith(joint_prefix):
                title = title[len(joint_prefix) :]
                add_joint_prefix = True
            title = title.replace(
                " and Senate Committee", f"{separator}Senate Committee"
            )
            title = title.replace(
                " and Assembly Committee", f"{separator}Assembly Committee"
            )
            committees = title.split(separator)
            title = " and ".join(committees)
            if add_joint_prefix:
                title = f"{joint_prefix}{title}"

            agenda_bills = []

            # Some committee events (committee floor meetings)
            #  do not have an agenda -> no link to agenda PDF
            try:
                # Second element contains: a link to the agenda pdf
                agenda = XPath(
                    './/a[@title="View the agenda for this meeting"]/@href'
                ).match_one(i[1])

                # Check PDF for start time
                agenda_start_time = next(AgendaStartTime(source=agenda).do_scrape())

                # Add bills from PDF
                for bill in Agenda(source=agenda).do_scrape():
                    agenda_bills.append(bill)

            # NV seems to have a lot of problems with these event agenda URLs
            # 404 is not uncommon, or weird failing redirects
            # so we catch those exceptions and keep moving
            except (
                SelectorError,
                scrapelib.HTTPError,
                requests.exceptions.TooManyRedirects,
            ):
                agenda = None
                agenda_start_time = ""

            # Get start date
            date = XPath(".//h3/a[2]/text()").match_one(i[0])

            # Remove day of the week information
            date = date.split(", ", 1)[1]

            if "[" in date:
                # Date contains "upon adjournment" instead of start time
                date_only = date.split("[")[0]
                date = f"{date_only}{agenda_start_time}"

            # To prevent strptime() from failing due to extra whitespace
            date = date.strip()

            date_and_time_match = self.time_in_date_re.search(date)
            if date_and_time_match:
                date = datetime.datetime.strptime(date, "%B %d, %Y %I:%M %p")
            else:
                date = datetime.datetime.strptime(date, "%B %d, %Y")

            # Third element contains: a list of locations
            locations = XPath(".//li/text()").match(i[2])

            # Build event, scrape bill ids from agenda, and yield it
            event = Event(
                start_date=self._TZ.localize(date),
                name=title,
                location_name=locations[0].replace("\u00a0", " "),
            )
            event.add_source(self.source.url)

            if agenda:
                event.add_document("Agenda", url=agenda, media_type="pdf")

            try:
                video_link = XPath(
                    ".//button[@title='View  committee meeting']/@onclick"
                ).match_one(i[1])
                if video_link:
                    video_link = video_link.replace("window.open('", "").replace(
                        "')", ""
                    )
                    event.add_media_link(
                        "Video", url=video_link, media_type="text/html"
                    )
            except SelectorError:
                pass

            try:
                minutes_link = XPath(
                    './/a[@title="View the minutes for this meeting"]/@href'
                ).match_one(i[1])
                if minutes_link:
                    event.add_document(
                        "Minutes", minutes_link, media_type=get_media_type(minutes_link)
                    )
            except SelectorError:
                pass

            # Add committees from title string
            for committee in committees:
                event.add_committee(committee)

            # Add any bills that were collected from PDF
            for bill in agenda_bills:
                event.add_bill(bill)

            yield event
            event_count += 1
        if event_count < 1:
            raise EmptyScrape


class NVEventScraper(Scraper, LXMLMixin):
    def scrape(self):
        yield from Meetings().do_scrape()
