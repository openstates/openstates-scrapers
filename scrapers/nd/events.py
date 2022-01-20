import dateutil.parser
import lxml
import pytz
from openstates.scrape import Scraper, Event


class NDEventScraper(Scraper):
    _tz = pytz.timezone("US/Central")

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

                yield event
