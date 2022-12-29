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
    # "house bill 123" "senate bill 123" "H.B. 4043" "HB 23" "SCR 29" "S. C. R 23"
    bill_regex = (
        r"((House Bill|Senate Bill|[HS]\.\s*[BCR]\.\s*([R]\.)*|H\.?\s*B\.?)\s*\d+)"
    )

    def scrape(self):
        com_urls = [
            ("Senate", "http://www.wvlegislature.gov/committees/senate/main.cfm"),
            ("House", "http://www.wvlegislature.gov/committees/House/main.cfm"),
            ("Interim", "http://www.wvlegislature.gov/committees/Interims/interims.cfm"),
        ]
        for chamber, url in com_urls:
            yield from self.scrape_committees(chamber, url)

    def scrape_committees(self, chamber, url):
        event_objects = set()
        page = self.lxmlize(url)
        page.make_links_absolute(url)
        # note house uses div#wrapleftcol and sen uses div#wrapleftcolr on some pages
        for link in page.xpath(
            '//div[contains(@id,"wrapleftcol")]/a[contains(@href,"agendas.cfm")]/@href'
        ):
            for event in self.scrape_committee_page(link):
                event_name = f"{chamber}#{event.name}#{event.start_date}#{event.end_date}#{event.location['name']}#{event.description}"[:500]
                if event_name in event_objects:
                    self.warning(f"Found duplicate {event_name}. Skipping.")
                    continue
                event_objects.add(event_name)
                event.dedupe_key = event_name
                yield event

    def scrape_committee_page(self, url):
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
        page = self.lxmlize(url)
        page.make_links_absolute(url)

        if page.xpath('//div[text()="Error"]'):
            return

        if not page.xpath('//div[@id="wrapleftcol"]/h3'):
            return

        com = page.xpath('//div[@id="wrapleftcol"]/h3[1]/text()')[0].strip()
        com = re.sub(r"[\s\-]+Agenda", "", com)
        when = page.xpath('//div[@id="wrapleftcol"]/h1[1]/text()')[0].strip()

        if "time to be announced" in when.lower() or "tba" in when.lower():
            when = re.sub("time to be announced", "", when, flags=re.IGNORECASE)
            when = re.sub("TBA", "", when, flags=re.IGNORECASE)

        when = re.sub(r"or\s+conclusion\s+(.*)", "", when, flags=re.IGNORECASE)

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
        )

        event.add_committee(com, note="host")

        for row in page.xpath('//div[@id="wrapleftcol"]/blockquote[1]/p'):
            if row.text_content().strip() != "":
                agenda = event.add_agenda_item(
                    row.text_content().strip().replace("\u25a1", "")
                )
                for bill in re.findall(self.bill_regex, row.text_content()):
                    bill_id = re.sub(r"\.\s*", "", bill[0], flags=re.IGNORECASE)
                    bill_id = re.sub(r"house bill", "HB", bill_id, flags=re.IGNORECASE)
                    bill_id = re.sub(r"senate bill", "SB", bill_id, flags=re.IGNORECASE)
                    agenda.add_bill(bill_id)

        event.add_source(url)

        yield event

    def clean_date(self, when):
        # Feb is a tough one, isn't it?
        # After feburary, februarary, febuary, just give up and regex it
        when = re.sub(r"feb(.*?)y", "February", when, flags=re.IGNORECASE)
        when = re.sub(r"Tuesdat", "Tuesday", when, flags=re.IGNORECASE)
        when = re.sub(r"Immediately(.*)", "", when, flags=re.IGNORECASE)
        when = re.sub(r"Time Announced(.*)", "", when, flags=re.IGNORECASE)
        when = re.sub(r"\d+ min\. After Floor Session", "", when, flags=re.IGNORECASE)
        when = re.sub(
            r"(?:Shortly| One Hour)?\s*(After|following)\s*(?:the)?\s*(?:second)?\s*Floor Session",
            "",
            when,
            flags=re.IGNORECASE,
        )
        when = re.sub(r"To Be Announced", "", when, flags=re.IGNORECASE)
        when = re.sub(r"TB(.*)", "", when, flags=re.IGNORECASE)
        when = re.sub(r"\*", "", when, flags=re.IGNORECASE)
        when = re.sub(
            r"\d+ minutes following the evening floor session(.*)",
            "",
            when,
            flags=re.IGNORECASE,
        )
        when = re.sub(
            r",?\s+following\s+floor\s+session", "", when, flags=re.IGNORECASE
        )
        when = re.sub(
            r"ONE HOUR BEFORE SENATE FLOOR SESSION(.*)", "", when, flags=re.IGNORECASE
        )
        when = re.sub(r"\d+ (mins\.|minutes) After (.*)", "", when, flags=re.IGNORECASE)
        when = when.replace("22021", "2021")
        when = when.replace("20201", "2021")
        when = when.replace("20202", "2020")
        when = re.sub(r",\s+\d+ mins following (.*)", "", when)
        # Convert 1:300PM -> 1:30PM
        when = re.sub(r"(\d0)0([ap])", r"\1\2", when, flags=re.IGNORECASE)

        # manual fix for nonsense date,
        # http://www.wvlegislature.gov/committees/House/house_com_agendas.cfm
        # ?Chart=agr&input=March%201,%202022
        if when == "March 1, 2022, PM":
            when = "March 1, 2022, 1:00 PM"

        return when
