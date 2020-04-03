import pytz
import datetime

from scrapers.utils import LXMLMixin
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

            date_with_time = "{} {}".format(date, time)

            location = row.xpath("td")[2].text_content().strip()

            # 11 South Union Street, Montgomery, Alabama, United States
            # TODO: IF location is "room (X)" add state house
            # TODO: REplace "state house" with address

            # 32°22′37.294″N 86°17′57.991″W

            # host = row.xpath('td')[3].text_content().strip()
            name = row.xpath("td")[3].text_content().strip()
            details = row.xpath("td")[4].text_content().strip()

            event = Event(
                start_date=self._TZ.localize(
                    datetime.datetime.strptime(date_with_time, self._DATETIME_FORMAT)
                ),
                name=name,
                location_name=location,
                description=details,
            )

            event.add_source(EVENTS_URL)

            yield event
