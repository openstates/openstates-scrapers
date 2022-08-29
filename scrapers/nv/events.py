import pytz
import datetime
import lxml

from utils import LXMLMixin
from openstates.scrape import Scraper, Event


class NVEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("PST8PDT")
    URL = "https://www.leg.state.nv.us/MeetingDisplay/CalendarOfMeetings/"

    # Note: The NV Site has three different calendars.
    # https://www.leg.state.nv.us/MeetingDisplay/CalendarOfMeetings/
    # is the primary calendar. The title is 2011-2012 but shows current events.
    # It appears to have the same information and more compared to
    # https://www.leg.state.nv.us/App/Calendar/A/
    # The the social calendar is at
    # https://www.leg.state.nv.us/socialCalendar/socialCalendarDisplay.cfm?date=05/01/2017
    # and is not being scraped

    def scrape(self):
        html = self.get(self.URL).text
        page = lxml.html.fromstring(html)

        for row in page.xpath('//table[@width="98%" and @cellpadding="3"]/tr'):
            yield self.scrape_event(row)

    def scrape_event(self, row):
        date_td = row.xpath("td[1]")[0]
        info_td = row.xpath("td[2]")[0]

        date = date_td.xpath("b")[0].text.strip()
        time = date_td.xpath("b/following-sibling::text()")[0].strip()

        date_and_time = "{} {}".format(date, time)
        start_date = datetime.datetime.strptime(date_and_time, "%m/%d/%y %I:%M %p")

        title = info_td.xpath("font[1]/strong")[0].text.strip()

        all_text = info_td.xpath("descendant-or-self::*/text()")
        notes = (line.strip() for line in all_text if line.strip())
        notes = list(notes)

        if len(notes) > 1:
            # Skip the first line, which is the title
            notes = notes[1:]
            # Split out the address
            address = notes[0]
            notes = notes[1:]
            # The rest just becomes the description
            notes = "\n".join(notes)
        else:
            address = "TBD"
            notes = notes[0]

        event = Event(
            start_date=self._TZ.localize(start_date),
            name=title,
            location_name=address,
            description=notes,
        )

        event.add_source(self.URL)

        if info_td.xpath('a[contains(font/text(),"agenda")]'):
            agenda_url = info_td.xpath("a/@href")[0]
            event.add_document("Agenda", url=agenda_url)

        yield event
