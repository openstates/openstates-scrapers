import dateutil.parser
import lxml
import pytz
import re
from openstates.scrape import Scraper, Event


class NDEventScraper(Scraper):
    _tz = pytz.timezone("US/Central")
    event_months = set()
    events = {}

    def scrape(self, session=None):

        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        # figuring out starting year from metadata
        for item in self.jurisdiction.legislative_sessions:
            if item["identifier"] == session:
                start_year = item["start_date"][:4]
                self.year = start_year
                break

        url = f"https://www.legis.nd.gov/assembly/{session}-{start_year}/committees/interim/committee-meeting-summary"

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for table in page.xpath('//table[contains(@class,"views-table")]'):
            com = table.xpath("caption/a")[0].text_content().strip()
            for row in table.xpath("tbody/tr"):
                date_link = row.xpath("td[1]/strong/a")[0]
                event_url = date_link.xpath("@href")[0]

                date = date_link.xpath("span")[0].text_content().strip()
                date = dateutil.parser.parse(date)
                date = self._tz.localize(date)

                self.event_months.add(date.strftime("%Y-%m"))

                location = "See Agenda"

                event = Event(name=com, start_date=date, location_name=location)

                event.add_source(event_url)

                for link in row.xpath("td[2]//a"):
                    link_text = link.text_content().strip()

                    # skip live broadcast links
                    if "video.legis" in link_text:
                        continue

                    event.add_document(
                        link_text, link.xpath("@href")[0], media_type="application/pdf"
                    )

                self.events[event_url] = event

        for year_month in self.event_months:
            self.scrape_calendar(year_month)

        for key in self.events:
            yield self.events[key]

    # the listing page has all the events and attachments, but no dates or locations
    # the calendar page has dates and locations, but no attachments
    def scrape_calendar(self, year_month):
        self.info(f"Scraping calendar for {year_month}")
        cal_url = f"https://ndlegis.gov/events/{year_month}"
        page = self.get(cal_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(cal_url)

        for row in page.xpath("//div[contains(@class,'calendar-item')]"):
            if row.xpath(
                ".//div[contains(@class,'event-count') and (contains(text(), '2 of') or contains(text(), '3 of'))]"
            ):
                self.info("Skipping later day of multi-day event")
                continue

            if not row.xpath(".//span[contains(@class,'date-display-start')]"):
                continue

            event_url = row.xpath(".//div[contains(@class,'event-title')]/a/@href")[0]

            if event_url not in self.events:
                self.info(f"Skipping {event_url}, not on hearing listing page.")
                continue

            event_time = row.xpath(
                ".//span[contains(@class,'date-display-start')]/text()"
            )[0]
            event_date = (
                self.events[event_url].as_dict()["start_date"].strftime("%Y-%m-%d")
            )
            new_start = f"{event_date} {event_time}"

            date = dateutil.parser.parse(new_start)
            date = self._tz.localize(date)
            self.events[event_url].__setattr__("start_date", date)

            if row.xpath(".//div[contains(@class,'vcard')]"):
                raw_loc = row.xpath(".//div[contains(@class,'vcard')]")[
                    0
                ].text_content()
                loc = raw_loc.strip()
                loc = re.sub(r"\s+", " ", loc)
                loc = loc.replace("State Capitol", "600 East Boulevard Avenue")
                loc_dict = {"name": loc, "note": "", "coordinates": None}
                if len(loc) > 0:
                    self.events[event_url].__setattr__("location", loc_dict)
