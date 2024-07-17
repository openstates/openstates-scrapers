from openstates.scrape import Scraper, Event
import dateutil
import json
import lxml.html
import pytz
import re


class MTEventScraper(Scraper):
    _tz = pytz.timezone("America/Denver")

    def scrape(self, start=None, end=None):
        url = "https://sg001-harmony.sliq.net/00309/Harmony/en/View/UpcomingEvents"

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//div[@class='divEvent']/a[1]"):
            yield from self.scrape_event(link.xpath("@href")[0])

    def scrape_event(self, url: str):
        html = self.get(url).text
        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        title = page.xpath("//span[@class='headerTitle']")[0].text_content()
        location = page.xpath("//span[@id='location']")[0].text_content()

        when_date = page.xpath("//div[@id='scheduleddate']")[0].text_content()
        when_time = page.xpath("//span[@id='scheduledStarttime']")[0].text_content()

        when = dateutil.parser.parse(f"{when_date} {when_time}")
        when = self._tz.localize(when)

        event = Event(
            name=title,
            location_name=location,
            start_date=when,
            classification="committee-meeting",
        )

        self.scrape_versions(event, html)

        event.add_source(url)

        yield event

    def scrape_versions(self, event: Event, html: str):
        matches = re.search(r"Handouts: (.*),", html)
        versions = json.loads(matches.group(1))
        for v in versions:
            event.add_document(
                v["Name"],
                v["HandoutFileUrl"],
                media_type="application/pdf",
                on_duplicate="ignore",
            )
