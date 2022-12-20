import dateutil.parser
import pytz
import re

from utils import LXMLMixin
from utils.events import match_coordinates
from openstates.scrape import Scraper, Event


class ALEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("US/Eastern")
    _DATETIME_FORMAT = "%m/%d/%Y %I:%M %p"

    def scrape(self):

        EVENTS_URL = (
            "http://www.legislature.state.al.us/aliswww/ISD/InterimMeetings.aspx"
        )
        rows = self.lxmlize(EVENTS_URL).xpath(
            '//table[@id="ContentPlaceHolder1_gvInterimMeeting"]/tr'
        )
        for row in rows[1:]:
            date = row.xpath("td")[0].text_content().strip()
            time = row.xpath("td")[1].text_content().strip()
            details = row.xpath("td")[4].text_content().strip()

            if time != "":
                date_with_time = "{} {}".format(date, time)
            else:
                # sometimes the time is the first part of the decription
                match = re.match(r"\s*\d+:\d+\s*[ap]m", details, flags=re.I)
                if match:
                    date_with_time = "{} {}".format(date, match.group())

            location = row.xpath("td")[2].text_content().strip()

            if re.match(r"^Room", location, flags=re.IGNORECASE):
                location = f"{location}, 11 South Union Street, Montgomery, Alabama, United States"

            # 11 South Union Street, Montgomery, Alabama, United States
            # TODO: IF location is "room (X)" add state house
            # TODO: REplace "state house" with address

            # 32°22′37.294″N 86°17′57.991″W

            # host = row.xpath('td')[3].text_content().strip()
            name = row.xpath("td")[3].text_content().strip()
            if name == "":
                continue

            event = Event(
                start_date=self._TZ.localize(dateutil.parser.parse(date_with_time)),
                name=name,
                location_name=location,
                description=details,
            )

            match_coordinates(
                {"11 south union": (32.37707594063977, -86.29919861850152)}
            )

            event.add_source(EVENTS_URL)

            yield event
