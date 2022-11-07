from openstates.scrape import Scraper, Event
import pytz
import logging
import dateutil.parser
from spatula import XPath, HtmlListPage


# TODO: Add pagination; need guidance on this
"""
While spatula's get_next_source() handles this for different URL's,
does spatula have a way to handle these buttons that seem to use JavaScript
to load the next series of events to display on the same page?
"""

# TODO: Feedback on proposed method for extracting year for event date
"""
The way this scraper is currently set up using spatula, the HtmlListPage
object is creating an item for every table row (ideal for creating events.
However, the table row only provides MM/DD + time, not year of the event
date. My idea for how to handle this:
    Use a selector (maybe outside of process_item()) to extract the year
    from an HTML element elsewhere on the page (like the November 08, 2021 to
    November 13, 2021 date range in a <span> above the table)
        - Problem: when we hit the event week that contains two different years
        (end of Dec to start of Jan)
        - Proposed Solution:
            - create two new attributes of EventList, year and year_changed
            - :year: string of the extracted starting year for the event range
            - :year_changed: boolean instantiated as False
            - A selector extracts the initial event year, saves it to `year`
            - In process_item(), a conditional statement checks if:
                - event date prior to Jan 7 AND `year_changed == False`
                - if both true, `year` will be incremented by 1, and
                `year_changed` will be reassigned to True
            - **NOTE** A conditional will need to be added when instantiating
            `year_changed` such that if the start of the date range <span>
            is between Jan 1st and Jan 7th upon initial page load, then
            `year_changed` is instantiated as `True`
                - Without a conditional check to cover this scenario, the first
                event would trigger an erroneous incrementing of `year` by 1.
**NOTE** Whether due to a glitch in their calendar, or some other reason (like
their web designer demonstrating functionality for this part of their new
page by using past events), ND's committee hearings page is showing events
for this time LAST YEAR (in 2021).
    - This scraper is being built assuming they will update this prior to start
    of January 2023 legislative session.
"""

# TODO: Determine best way to store which Bill the committee work is on
"""
This will support Enview team in linking events to bills.
"""


class EventList(HtmlListPage):
    events_path = "/legend/committee/hearings/public-schedule/"
    source = f"https://www.ndlegis.gov{events_path}"
    selector = XPath("//tbody//tr[1]")
    _tz = pytz.timezone("US/Central")

    def process_item(self, item):
        item_text_list = item.text_content().strip().split("\n")
        item_list = [x.strip() for x in item_text_list if len(x.strip()) > 0]

        description = item_list[0] + ", " + item_list[4]

        raw_date_time, committee, location = item_list[1:4]

        local_date = dateutil.parser.parse(raw_date_time)
        date_with_offset = self._tz.localize(local_date)

        event = Event(
            name=committee,
            location_name=location,
            description=description,
            start_date=date_with_offset,
        )

        event.add_source(self.source.url)

        return event


class NewNDEventScraper(Scraper):
    def scrape(self, session=None):
        # Event object needs name, start_date, and location_name
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        event_list = EventList()
        yield from event_list.do_scrape()
