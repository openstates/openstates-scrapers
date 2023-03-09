import pytz
import datetime

# import lxml

from utils import LXMLMixin

# from utils.events import match_coordinates
from openstates.scrape import Scraper, Event

from spatula import HtmlPage, PdfPage, URL, XPath
import json
import re


bills_re = re.compile(
    r"(SJR|AR|AJR|IP|SCR|SB|ACR|SR|AB)\s{0,5}0*(\d+)", flags=re.IGNORECASE
)


class Agenda(PdfPage):
    def process_page(self):
        # Simplify text to make regex simpler
        self.text = self.text.replace(". ", "").replace(".", "")

        # Find all bill ids
        bills = bills_re.findall(self.text)

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
            url=f"https://www.leg.state.nv.us/App/NELIS/REL/{session_id}/Meetings?Meetings=System.Collections.Generic.List%601%5BNvLeg.Models.Nelis.SessionManager.Views.MeetingComposite%5D&MeetingsFilters=System.DateTime%5B%5D&ShowFloorMeetings=False&ShowCommitteeMeetings=True&ShowConferenceCommittees=False",
            data=json.dumps(
                {
                    "MeetingsFilters": "3/9/2023",
                    # "MeetingsFilters": "1/1/9999",
                    "ShowCommitteeMeetings": "true",
                    # "ShowCommitteeMeetings": "false",
                    "ShowFloorMeetings": "false",
                    "ShowConferenceCommittees": "false"
                    # X-Requested-With: XMLHttpRequest
                }
            ),
        )
        yield CurrentMeetings(source=session_link)


class CurrentMeetings(HtmlPage):
    _TZ = pytz.timezone("PST8PDT")
    example_source = "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Meetings"

    def process_page(self):
        container = XPath('//div[@id="meetings-list"]').match_one(self.root)

        meetings = []
        cur_row = []
        # The container element contains meeting information - each meeting has
        # info spread across up to 3 divs, with a <hr> after each section - The
        # following code finds all of these sections with 3 divs and places them
        # into the meetings variable
        for i in container.getchildren():
            if i.tag == "div":
                cur_row.append(i)
            elif i.tag == "hr":
                # Only add if all three elements are present - missing elements
                # indicate that this section is cancelled or floor meeting
                if len(cur_row) == 3:
                    meetings.append(cur_row)
                cur_row = []

        for i in meetings:
            # First element contains: the title and date
            title = XPath(".//h3/a[1]/text()").match_one(i[0])
            # Clean up title by removing trailing "-"
            date = XPath(".//h3/a[2]/text()").match_one(i[0])
            # Remove day of the week from date text
            date = date.split(", ", 1)[1]
            # Create date object from date string
            date = datetime.datetime.strptime(date, "%B %d, %Y %I:%M %p")

            # Second element contains: a link the the agenda pdf
            agenda = XPath(
                './/a[@title="View the agenda for this meeting"]/@href'
            ).match_one(i[1])

            # Third element contains: a list of locations
            locations = XPath(".//li/text()").match(i[2])
            # print(chamber, title, date, agenda, locations)
            event = Event(
                start_date=self._TZ.localize(date),
                name=title,
                location_name=locations[0],
                # description="asdf",
            )
            event.add_source(self.source.url)
            event.add_committee(title, note="host")
            event.add_document("Agenda", url=agenda)
            for bill in Agenda(source=agenda).do_scrape():
                event.add_bill(bill)
            yield event


class NVEventScraper(Scraper, LXMLMixin):
    def scrape(self):
        yield from Meetings().do_scrape()
