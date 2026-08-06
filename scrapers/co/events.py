import dateutil
import pytz

import lxml
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

from utils.events import match_coordinates
from utils import LXMLMixin


class COEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("America/Denver")

    chamber_names = {"upper": "Senate", "lower": "House"}

    schedule_url = "https://leg.colorado.gov/schedule"

    def clean(self, text):
        if isinstance(text, list):
            if not text:
                return ""
            first = text[0]
            if hasattr(first, "text_content"):
                return first.text_content().strip()
            return str(first).strip()
        if hasattr(text, "text_content"):
            return text.text_content().strip()
        return str(text).strip()

    def scrape(self):
        yield from self.scrape_upcoming_events()

        # TODO: past events aren't stable enough yet, but write a scraper to get
        # additional info when it's posted

    def scrape_upcoming_events(self):
        """
        Fetches the schedule page (a single static page) and yields Events.

        The site has two known layouts:

        1. Interim layout (currently active): ``div.interim-schedule-table``
           blocks, each with an ``h3`` date heading and a table of events with
           columns Time / Activity / Location / Agenda / Audio.

        2. In-session layout (used when the legislature is meeting):
           ``div.tab-content.standard-table`` day blocks with an ``h3`` date
           heading and a similar events table. This is the legacy layout the
           previous scraper targeted, kept as a fallback.
        """
        response = self.get(self.schedule_url)
        page = lxml.html.fromstring(response.content)
        page.make_links_absolute(self.schedule_url)

        yielded = 0

        # 1) Interim schedule layout (single static page, no pagination)
        for day_block in page.cssselect("div.interim-schedule-table"):
            heading = day_block.cssselect("h3")
            if not heading:
                continue
            event_date = self.clean(heading)
            for row in day_block.cssselect("table tbody tr"):
                for event in self.scrape_event_row(row, event_date):
                    yielded += 1
                    yield event

        # 2) In-session layout fallback (legacy structure)
        if yielded == 0:
            for day_block in page.cssselect("div.tab-content.standard-table"):
                heading = day_block.cssselect("h3")
                if not heading:
                    continue
                event_date = self.clean(heading)
                for row in day_block.cssselect("tbody tr"):
                    for event in self.scrape_event_row(row, event_date):
                        yielded += 1
                        yield event

        if yielded == 0:
            # Neither layout matched or the schedule is genuinely empty
            # (e.g. between interim and session). Raise EmptyScrape so
            # openstates records a clean empty run instead of ScrapeError.
            raise EmptyScrape

    def scrape_event_row(self, row: lxml.html.HtmlElement, start_day: str):
        start_time = self.clean(row.xpath("td[1]"))

        # Committee/activity name: prefer the link text, fall back to cell text
        com_link = row.xpath("td[2]//a")
        if com_link:
            com_name = self.clean(com_link)
        else:
            com_name = self.clean(row.xpath("td[2]"))

        if not com_name or not start_time:
            return

        location = self.clean(row.xpath("td[3]"))
        location = f"{location}, 200 E Colfax Ave, Denver, CO 80203"

        start = f"{start_day} {start_time}"
        try:
            start = dateutil.parser.parse(start, fuzzy=True)
        except (ValueError, OverflowError):
            self.warning(f"Could not parse date/time for {com_name}: {start!r}")
            return
        start = self._tz.localize(start)

        event = Event(com_name, start, location, status="tentative")
        event.add_committee(com_name)

        # Agenda cell (td[4]) may contain an HTML Agenda link and/or a PDF link
        agenda_link = row.xpath(
            "td[4]//a[contains(translate(text(), 'AGENDA', 'agenda'), 'agenda')]"
        )
        if agenda_link:
            agenda_url = agenda_link[0].xpath("@href")[0]
            event.add_document(
                "Agenda", agenda_url, media_type="text/html", classification="agenda"
            )
            self.scrape_agenda_page(event, agenda_url)
            event.add_source(agenda_url)

        pdf_agenda_link = row.xpath(
            "td[4]//a[contains(translate(text(), 'PDF', 'pdf'), 'pdf')]"
        )
        if pdf_agenda_link:
            pdf_agenda_url = pdf_agenda_link[0].xpath("@href")[0]
            event.add_document(
                "Agenda",
                pdf_agenda_url,
                media_type="application/pdf",
                classification="agenda",
            )

        # Audio/listen link (td[5]) — surfaced as a media link when present
        audio_link = row.xpath("td[5]//a/@href")
        if audio_link:
            try:
                event.add_media_link("Audio", audio_link[0], media_type="text/html")
            except Exception:
                # add_media_link signature/availability varies; ignore if unsupported
                pass

        match_coordinates(event, {"200 E Colfax": (39.7393, -104.9645)})

        event.add_source(self.schedule_url)

        yield event

    def scrape_agenda_page(self, event: Event, url: str):
        page = self.get(url).content
        page = lxml.html.fromstring(page)

        # New layout: vertical table where each hearing item is a row with
        # <th>Hearing Item</th><td><span>text</span></td>.
        rows = page.cssselect(
            "section.hearing-items-block table.vertical-table tbody tr"
        )
        # Legacy layout fallback: horizontal table under the same section.
        if not rows:
            rows = page.cssselect("section.hearing-items-block tbody tr")

        for row in rows:
            # Prefer text inside the <td><span>...</span></td> cell
            span_text = row.xpath("td//span")
            if span_text:
                item = self.clean(span_text)
            else:
                td = row.xpath("td")
                if not td:
                    continue
                item = self.clean(td)
            if item:
                event.add_agenda_item(item)
