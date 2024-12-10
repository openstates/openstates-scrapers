from typing import Union

from openstates.scrape import Scraper, Event
from utils.events import match_coordinates
import datetime
import dateutil
import json
import lxml.html
import pytz
import re


class MTEventScraper(Scraper):
    _tz = pytz.timezone("America/Denver")
    # the same MT event can be listed more than once at the source URLs
    # where each listing is an alternate media stream (video vs. audio)
    # so we need to do some data combining before yielding
    _events = []

    def scrape(self):

        self.scrape_upcoming()

        # scrape events from this month, and last month
        today = datetime.date.today()
        self.scrape_cal_month(today)
        self.scrape_cal_month(today + dateutil.relativedelta.relativedelta(months=-1))
        for event in self._events:
            yield event

    def scrape_upcoming(self):
        url = "https://sg001-harmony.sliq.net/00309/Harmony/en/View/UpcomingEvents"

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//div[@class='divEvent']/a[1]"):
            self.scrape_event(link.xpath("@href")[0])

    def scrape_cal_month(self, when: datetime.datetime.date):
        date_str = when.strftime("%Y%m01")
        self.info(f"Scraping month {date_str}")
        #  https://sg001-harmony.sliq.net/00309/Harmony/en/View/Month/20240717/-1
        url = f"https://sg001-harmony.sliq.net/00309/Harmony/en/api/Data/GetContentEntityByMonth/{date_str}/-1?lastModifiedTime=20000201050000000"
        page = self.get(url).json()
        for row in page["ContentEntityDatas"]:
            when = dateutil.parser.parse(row["ScheduledStart"])
            if when.date() < datetime.datetime.today().date():
                event_id = str(row["Id"])
                event_url = f"https://sg001-harmony.sliq.net/00309/Harmony/en/PowerBrowser/PowerBrowserV2/1/-1/{event_id}"
                self.scrape_event(event_url)

    def scrape_event(self, url: str):
        html = self.get(url).text
        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        title = page.xpath("//span[@class='headerTitle']")[0].text_content().strip()
        location = page.xpath("//span[@id='location']")[0].text_content().strip()

        # handle edge case where event is named simply "Other"
        # append the location name to force it into not being a duplicate
        if title.lower() == "other":
            title = f"{title} - {location}"

        # handle edge case of "test" event, just ignore that
        if title.lower() == "test":
            return

        if location.lower()[0:4] == "room":
            location = f"{location}, 1301 E 6th Ave, Helena, MT 59601"

        when_date = page.xpath("//div[@id='scheduleddate']")[0].text_content()
        when_time = page.xpath("//span[@id='scheduledStarttime']")[0].text_content()

        when = dateutil.parser.parse(f"{when_date} {when_time}")
        when = self._tz.localize(when)

        # Check if event already exists in the self._events list
        # and if so, add data to that instead of creating duplicate
        existing_event = self.check_for_existing_event(title, when)
        if existing_event is None:
            # No existing event found, create one
            event = Event(
                name=title,
                location_name=location,
                start_date=when,
                classification="committee-meeting",
            )
        else:
            event = existing_event

        self.scrape_versions(event, html)
        self.scrape_media(event, html)

        if existing_event is None:
            event.add_source(url)

        if "HB" not in title.lower() and "SB" not in title.lower():
            event.add_committee(title)

        match_coordinates(
            event,
            {
                "1301 E 6th Ave, Helena": ("46.5857", "-112.0184"),
            },
        )

        # Make sure we add any new event to the list
        if existing_event is None:
            self._events.append(event)

    def check_for_existing_event(
        self, title: str, start_date: datetime.datetime.date
    ) -> Union[Event, None]:
        for event in self._events:
            if event.name == title and event.start_date == start_date:
                return event

        return None

    # versions and media are in the 'dataModel' js variable on the page
    def scrape_versions(self, event: Event, html: str):
        matches = re.search(r"Handouts:\s?(.*),", html)
        versions = json.loads(matches.group(1))
        for v in versions:
            event.add_document(
                v["Name"],
                v["HandoutFileUrl"],
                media_type="application/pdf",
                on_duplicate="ignore",
            )

    def scrape_media(self, event: Event, html: str):
        # MT has livestream archives available as m3u8 files
        # these can be played only by certain players, for example:
        # https://livepush.io/hlsplayer/index.html
        matches = re.search(r"Media:\s?(.*),", html)
        media = json.loads(matches.group(1))
        if "children" in media and media["children"] is not None:
            for m in media["children"]:
                event.add_media_link(
                    m["textTags"]["DESCRIPTION"]["text"],
                    m["textTags"]["URL"]["text"],
                    media_type="application/vnd",
                    on_duplicate="ignore",  # we are combining links from duplicate "event" listings into one
                )
