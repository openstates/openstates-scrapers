import pytz
import datetime
import dateutil.parser
import lxml
import re
from openstates.scrape import Scraper, Event


class IDEventScraper(Scraper):
    _tz = pytz.timezone("America/Boise")

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        if chamber == "upper":
            url = "https://legislature.idaho.gov/sessioninfo/agenda/sagenda/"
        elif chamber == "lower":
            url = "https://legislature.idaho.gov/sessioninfo/agenda/hagenda/"

        page = self.get(url).content
        page = lxml.html.fromstring(page)

        for row in page.xpath('//div[@id="ai1ec-container"]/div'):
            month = row.xpath(".//div[contains(@class,'calendarHeader')]/div[contains(@class,'date')]/text()")[0].strip()
            day = row.xpath(".//div[contains(@class,'calendarHeader')]/div[contains(@class,'date')]/span/text()")[0].strip()

            time_and_loc = row.xpath(".//div[contains(@class,'calendarHeader')]/div[contains(@class,'abbr')]/h2/text()")
            time = time_and_loc[0].strip()
            loc = time_and_loc[1].strip()

            if 'not meet' in time.lower():
                continue

            start = dateutil.parser.parse(f"{month} {day} {time}")
            start = self._tz.localize(start)

            com = row.xpath(".//div[contains(@class,'calendarHeader')]/div[contains(@class,'day')]/h2/a/text()")[0].strip()

            event = Event(
                name=com,
                start_date=start,
                location_name=loc,
                classification="committee-meeting",
            )

            event.add_participant(com, type="committee", note="host")

            print(month, day, time, loc, com)

            event.add_source(url)
            yield event