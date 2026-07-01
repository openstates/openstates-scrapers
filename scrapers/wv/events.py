import dateutil.parser
import datetime
import pytz
import re
from openstates.scrape import Scraper
from openstates.scrape import Event
from utils import LXMLMixin


class WVEventScraper(Scraper, LXMLMixin):
    verify = False
    _tz = pytz.timezone("US/Eastern")

    interims_url = "http://www.wvlegislature.gov/committees/Interims/interims.cfm"

    def scrape(self):
        com_urls = [
            ("Senate", "http://www.wvlegislature.gov/committees/senate/main.cfm"),
            ("House", "http://www.wvlegislature.gov/committees/House/main.cfm"),
            ("Interim", self.interims_url),
        ]
        for chamber, url in com_urls:
            yield from self.scrape_committees(chamber, url)

        # The per-committee crawl above only follows "agendas.cfm" links, which
        # misses meetings that are only published on the consolidated interim
        # committee schedule (e.g. the June 14-16 Canaan Valley meetings).
        # Scrape those schedule pages directly so those events are captured.
        yield from self.scrape_interim_schedules(self.interims_url)

    def scrape_committees(self, chamber, url):
        event_objects = set()
        page = self.lxmlize(url)
        page.make_links_absolute(url)
        # note house uses div#wrapleftcol and sen uses div#wrapleftcolr on some pages
        for link in page.xpath(
            '//div[contains(@id,"wrapleftcol")]/a[contains(@href,"agendas.cfm")]/@href'
        ):
            for event in self.scrape_committee_page(link):
                event_name = f"{chamber}#{event.name}#{event.start_date}#{event.end_date}#{event.location['name']}#{event.description}"[
                    :500
                ]
                if event_name in event_objects:
                    self.warning(f"Found duplicate {event_name}. Skipping.")
                    continue
                event_objects.add(event_name)
                event.dedupe_key = event_name
                yield event

    def scrape_interim_schedules(self, url):
        """Scrape the consolidated interim committee meeting schedule.

        The interims landing page lists each interim meeting block (e.g.
        "June 14-16") in its right-hand column, linking to an
        ``intcomsched.cfm`` page that holds a per-day table of committee
        meetings. These meetings are not always reachable via the per-
        committee "agendas.cfm" crawl, so scrape the schedule directly.
        """
        page = self.lxmlize(url)
        page.make_links_absolute(url)

        current_year = datetime.datetime.today().year
        event_objects = set()

        sched_links = set(page.xpath('//a[contains(@href, "intcomsched.cfm")]/@href'))
        for link in sched_links:
            # Links look like intcomsched.cfm?day1=06/14/2026 - use the
            # year in the query string to skip past meeting blocks.
            match = re.search(r"day1=\d{1,2}/\d{1,2}/(\d{4})", link)
            if match and int(match.group(1)) < current_year:
                continue

            for event in self.scrape_interim_schedule_page(link):
                event_name = f"Interim#{event.name}#{event.start_date}#{event.end_date}#{event.location['name']}#{event.description}"[
                    :500
                ]
                if event_name in event_objects:
                    self.warning(f"Found duplicate {event_name}. Skipping.")
                    continue
                event_objects.add(event_name)
                event.dedupe_key = event_name
                yield event

    def scrape_interim_schedule_page(self, url):
        self.info(f"GET {url}")
        page = self.lxmlize(url)
        page.make_links_absolute(url)

        if page.xpath('//div[text()="Error"]'):
            return

        # Each meeting day is an <h2> heading followed by a table of rows.
        for heading in page.xpath('//main[@id="wrapper"]/h2'):
            day_text = heading.text_content().strip()
            if not day_text:
                continue

            # e.g. "Monday, June 15, 2026"
            try:
                day = dateutil.parser.parse(self.clean_date(day_text))
            except (ValueError, OverflowError):
                self.warning(f"Could not parse interim schedule date: {day_text}")
                continue

            # The table with the day's meetings immediately follows the h2.
            table = heading.xpath("following-sibling::table[1]")
            if not table:
                continue

            for row in table[0].xpath(".//tr[td]"):
                yield from self.parse_interim_schedule_row(row, day, url)

    def parse_interim_schedule_row(self, row, day, source_url):
        cells = row.xpath("./td")
        if len(cells) < 4:
            return

        convene = cells[0].text_content().strip()
        adjourn = cells[1].text_content().strip()
        where = cells[3].text_content().strip()

        # The committee cell holds either a linked committee name plus a
        # separate "- Agenda" link, or plain text for site tours/presentations
        # (e.g. "Dolly Sods"). It may also carry a status suffix such as
        # "- CANCELLED" or "- JOINT MEETING".
        com_link = cells[2].xpath('.//a[contains(@href, "committee.cfm")]')
        if com_link:
            com = com_link[0].text_content().strip()
        else:
            com = cells[2].text_content().strip()

        raw_com_text = cells[2].text_content()
        status = "tentative"
        if "cancel" in raw_com_text.lower():
            status = "cancelled"

        # Strip trailing annotations like "- CANCELLED" or "- JOINT MEETING"
        # from the committee name (they're captured via status/description
        # instead).
        com = re.sub(
            r"\s*[-–]\s*(CANCELLED|CANCELED|JOINT MEETING|POSTPONED|RESCHEDULED)\s*$",
            "",
            com,
            flags=re.IGNORECASE,
        )
        com = re.sub(r"\s+", " ", com).strip()

        if not com:
            return

        # Combine the meeting day with the convene time so events aren't
        # incorrectly set to midnight.
        start_date = self.combine_date_time(day, convene)

        end_date = ""
        if adjourn:
            end_date = self.combine_date_time(day, adjourn)

        agenda_link = cells[2].xpath('.//a[contains(@href, "genda.cfm")]/@href')

        event = Event(
            name=com,
            start_date=start_date,
            end_date=end_date,
            location_name=where or "See agenda",
            classification="committee-meeting",
            status=status,
        )
        event.add_committee(com, note="host")
        event.add_source(source_url)

        # A committee.cfm link identifies the actual (non-tour) committees.
        if com_link:
            event.add_source(com_link[0].get("href"))

        if agenda_link:
            self.scrape_interim_agenda_page(event, agenda_link[0])

        yield event

    def scrape_interim_agenda_page(self, event, url):
        self.info(f"GET {url}")
        page = self.lxmlize(url)
        page.make_links_absolute(url)

        if page.xpath('//div[text()="Error"]'):
            return

        event.add_source(url)

        # The agenda body is the first blockquote under the main wrapper.
        rows = page.xpath('//main[@id="wrapper"]/blockquote[1]/p')
        self.parse_agenda_items(event, rows)

    def combine_date_time(self, day, time_text):
        """Combine a parsed date with a time string, localized to Eastern.

        Falls back to the bare (midnight) date if the time can't be parsed,
        but that should be rare for the interim schedule which always lists
        an explicit convene time.
        """
        time_text = (time_text or "").strip()
        if time_text:
            try:
                parsed = dateutil.parser.parse(
                    f"{day.strftime('%Y-%m-%d')} {time_text}"
                )
                return self._tz.localize(parsed)
            except (ValueError, OverflowError):
                self.warning(f"Could not parse interim time: {time_text}")

        return self._tz.localize(datetime.datetime(day.year, day.month, day.day))

    def scrape_committee_page(self, url):
        self.info(f"GET {url}")
        # grab the first event, then look up the pages for the table entries
        page = self.lxmlize(url)
        page.make_links_absolute(url)

        # if the page starts w/ a meeting
        if page.xpath('//div[@id="wrapleftcol"]/h1'):
            yield from self.scrape_meeting_page(url)

        for row in page.xpath('//td/a[contains(@href, "agendas.cfm")]'):
            if len(row.xpath("text()")) == 0:
                continue

            # meeting pages show events going back years
            # so just grab this cal year and later
            when = row.xpath("text()")[0].strip()
            when = when.split("-")[0]
            when = self.clean_date(when)

            # manual fix for un-yeared leap year meeting
            # on Senate Interstate Cooperation Committee
            if when == "February 29":
                continue

            when = dateutil.parser.parse(when)
            if when.year >= datetime.datetime.today().year:
                yield from self.scrape_meeting_page(row.xpath("@href")[0])

    def scrape_meeting_page(self, url):
        self.info(f"GET {url}")
        page = self.lxmlize(url)
        page.make_links_absolute(url)

        if page.xpath('//div[text()="Error"]'):
            return

        if not page.xpath('//div[@id="wrapleftcol"]/h3'):
            return

        com = page.xpath('//div[@id="wrapleftcol"]/h3[1]/text()')[0].strip()
        com = re.sub(r"[\s\-]+Agenda", "", com)
        when = page.xpath('//div[@id="wrapleftcol"]/h1[1]/text()')[0].strip()

        if when == "test, test" or when == ",":
            # Ignore test page
            return

        if "time to be announced" in when.lower() or "tba" in when.lower():
            when = re.sub("time to be announced", "", when, flags=re.IGNORECASE)
            when = re.sub("TBA", "", when, flags=re.IGNORECASE)

        status = "tentative"

        if "cancelled" in when.lower():
            when = re.sub(r"cancelled", "", when, flags=re.IGNORECASE)

        when = re.sub(r"or\s+conclusion\s+(.*)", "", when, flags=re.IGNORECASE)
        when = re.sub(r", After Session Ends", ", 5:00 PM", when, flags=re.IGNORECASE)
        when = re.sub(
            r", 30 Minutes Following House Floor Session", "", when, flags=re.IGNORECASE
        )
        when = re.sub(r",?\s+After Floor", "", when, flags=re.IGNORECASE)

        when = when.split("-")[0]
        when = self.clean_date(when)
        when = dateutil.parser.parse(when)
        when = self._tz.localize(when)

        # we check for this elsewhere, but just in case the very first event on a committee page is way in the past
        if when.year < datetime.datetime.today().year:
            return

        where = page.xpath(
            '//div[@id="wrapleftcol"]/*[contains(text(), "Location")]/text()'
        )[0].strip()
        desc = (
            page.xpath('//div[@id="wrapleftcol"]/blockquote[1]')[0]
            .text_content()
            .strip()
        )
        event = Event(
            name=com,
            start_date=when,
            location_name=where,
            classification="committee-meeting",
            # descriptions have a character limit
            description=desc,
            status=status,
        )

        event.add_committee(com, note="host")

        self.parse_agenda_items(
            event,
            page.xpath('//div[@id="wrapleftcol"]/blockquote[1]/p'),
        )

        event.add_source(url)

        yield event

    def parse_agenda_items(self, event, rows):
        """Add agenda items (and any linked bills) to an event.

        ``rows`` should be an iterable of <p> elements from an agenda
        blockquote. Bill references embedded in the text are parsed and
        linked to the agenda item.
        """
        component_re = re.compile(r"([A-Z]+)\s*(\d+)", flags=re.IGNORECASE)
        period_and_whitespace_re = re.compile(r"\.\s*", flags=re.IGNORECASE)
        house_bill_re = re.compile(r"house bill", flags=re.IGNORECASE)
        senate_bill_re = re.compile(r"senate bill", flags=re.IGNORECASE)

        for row in rows:
            if row.text_content().strip() == "":
                continue

            agenda = event.add_agenda_item(
                row.text_content().strip().replace("\u25a1", "")
            )

            # Matches (SJR, HCR, HB, HR, SCR, SB, HJR, SR) + id
            # Allows for house, senate, joint, or bill to be fully spelled out
            # Allows for "." after H, S, J, C, and B
            # Allows for up to two spaces before the id
            bills = re.findall(
                r"((S\.?|Senate|H\.?|House)\s?((J|C|Joint)\.?\s?)?(B\.?|Bill|R\.?)\s?\s?(\d+))",
                row.text_content(),
                flags=re.IGNORECASE,
            )

            for bill in bills:
                bill_id = period_and_whitespace_re.sub("", bill[0])
                bill_id = house_bill_re.sub("HB", bill_id)
                bill_id = senate_bill_re.sub("SB", bill_id)

                # Final step to set correct number of spaces in the id
                components = component_re.search(bill_id)
                bill_id = f"{components.group(1)} {int(components.group(2))}"

                agenda.add_bill(bill_id)

    def clean_date(self, when):
        # Remove all text after the third comma to make sure no extra text
        # is included in the date. Required to correctly parse text like this:
        # "Friday, March 3, 2023, Following wrap up of morning agenda"
        when = ",".join(when.split(",")[:3])

        removals = [
            r"(\d+|Thirty) (min\.|mins\.|minutes) After (.*)",
            r"Immediately(.*)",
            r"Time Announced(.*)",
            r"(?:Shortly| One Hour)?\s*(After|following)\s*(?:the)?\s*(?:second)?\s*Floor Session",
            r"Changed to",
            r"at end of floor session",
            r"TB(.*)",
            r"\*",
            r"\d+ minutes following (the evening floor|conclusion of floor)?\s*session(.*)",
            r",?\s+following\s+floor\s+session",
            r"ONE HOUR BEFORE SENATE FLOOR SESSION(.*)",
            r",\s+\d+ mins following (.*)",
            r", To be Announced on the Floor",
        ]

        for removal in removals:
            when = re.sub(removal, "", when, flags=re.IGNORECASE)

        # Feb is a tough one, isn't it?
        # After feburary, februarary, febuary, just give up and regex it
        when = re.sub(r"feb(.*?)y", "February", when, flags=re.IGNORECASE)
        when = re.sub(r"Tuesdat", "Tuesday", when, flags=re.IGNORECASE)
        when = when.replace("Thursady", "Thursday")
        when = when.replace("22021", "2021")
        when = when.replace("20201", "2021")
        when = when.replace("20202", "2020")
        when = when.replace("9:AM", "9:00AM")
        # Convert 1:300PM -> 1:30PM
        when = re.sub(r"(\d0)0([ap])", r"\1\2", when, flags=re.IGNORECASE)

        # manual fix for nonsense date,
        # http://www.wvlegislature.gov/committees/House/house_com_agendas.cfm
        # ?Chart=agr&input=March%201,%202022
        if when == "March 1, 2022, PM":
            when = "March 1, 2022, 1:00 PM"

        when = re.sub(r"\s+", " ", when)
        return when
