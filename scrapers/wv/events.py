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

    def scrape(self):
        com_urls = [
        ("Senate", "http://www.wvlegislature.gov/committees/senate/main.cfm"),
        ("House", "http://www.wvlegislature.gov/committees/House/main.cfm"),
        (
            "Interim",
            "http://www.wvlegislature.gov/committees/Interims/interims.cfm",
        ),
    ]
        for chamber, url in com_urls:
            yield from self.scrape_committees(chamber, url)



        yield from self._scrape_interim_committees_page(
            "http://www.wvlegislature.gov/committees/Interims/interims.cfm"
        )

    def _scrape_interim_committees_page(self, url):
        self.info(f"Scraping interim committees page: {url}")
        page = self.lxmlize(url)
        page.make_links_absolute(url)

        committee_links = page.xpath('//div[@id="wrapleftcol"]/a[contains(@href, "committee.cfm")]/@href')
        self.info(f"Found {len(committee_links)} interim committee links on {url}")
        for link in committee_links:
            yield from self._scrape_interim_committee_detail(link)

    def _scrape_interim_committee_detail(self, committee_url):
        self.info(f"Scraping interim committee detail page: {committee_url}")
        page = self.lxmlize(committee_url)
        page.make_links_absolute(committee_url)

        agenda_archive_link = page.xpath('//div[@class="int-section"]/h2[text()="Agendas"]/following-sibling::a[contains(@href, "agenda.cfm?abb=")]/@href')
        if agenda_archive_link:
            yield from self._scrape_agenda_archive_page(agenda_archive_link[0])

    def _scrape_agenda_archive_page(self, archive_url):
        self.info(f"Scraping agenda archive page: {archive_url}")
        page = self.lxmlize(archive_url)
        page.make_links_absolute(archive_url)

        agenda_links = page.xpath('//table[@class="tabborder"]//td[@class="tdborder"]/a[contains(@href, "agenda.cfm?recordid=")]/@href')
        self.info(f"Found {len(agenda_links)} individual agenda links on {archive_url}")
        for agenda_link in agenda_links:
            yield from self.scrape_meeting_page(agenda_link)

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
        self.info(f"Scraping meeting page: {url}")
        page = self.lxmlize(url)
        page.make_links_absolute(url)

        if page.xpath('//div[text()="Error"]'):
            self.warning(f"Error page found for {url}")
            return

        # Try XPath for interim committee pages
        com_xpath_interim = page.xpath('//div[@id="wrapleftcol"]/h3[1]/text()')
        when_xpath_interim = page.xpath('//div[@id="wrapleftcol"]/h1[1]/text()')
        where_xpath_interim = page.xpath('//div[@id="wrapleftcol"]/*[contains(text(), "Location")]/text()')
        desc_xpath_interim = page.xpath('//div[@id="wrapleftcol"]/blockquote[1]')

        # Try XPath for senate/house committee pages (alternate structure)
        com_xpath_alternate = page.xpath('//div[@id="wrapleftcol"]/h1[1]/text()')
        when_xpath_alternate = page.xpath('//div[@id="wrapleftcol"]/h2[1]/text()')
        where_xpath_alternate = page.xpath('//div[@id="wrapleftcol"]/strong[1]/text()')
        desc_xpath_alternate = page.xpath('//div[@id="wrapleftcol"]/blockquote[@class="textcontainer"][1]')


        if com_xpath_interim and when_xpath_interim:
            com = com_xpath_interim[0].strip()
            when = when_xpath_interim[0].strip()
            where = where_xpath_interim[0].strip() if where_xpath_interim else "N/A"
            desc = desc_xpath_interim[0].text_content().strip() if desc_xpath_interim else "N/A"
        elif com_xpath_alternate and when_xpath_alternate:
            com = com_xpath_alternate[0].strip()
            when = when_xpath_alternate[0].strip()
            where = where_xpath_alternate[0].strip() if where_xpath_alternate else "N/A"
            desc = desc_xpath_alternate[0].text_content().strip() if desc_xpath_alternate else "N/A"
        else:
            self.warning(f"Could not find committee header or when header for {url}. Skipping event creation.")
            return

        self.info(f"Committee: {com} (from {url})")
        com = re.sub(r"[\s\-]+Agenda", "", com)
        self.info(f"When: {when} (from {url})")
        self.info(f"Location: {where} (from {url})")
        self.info(f"Description: {desc[:100]}... (from {url})") # Truncate description for logs

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

        for row in page.xpath('//div[@id="wrapleftcol"]/blockquote[1]/p'):
            if row.text_content().strip() != "":
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

                component_re = re.compile(r"([A-Z]+)\s*(\d+)", flags=re.IGNORECASE)
                period_and_whitespace_re = re.compile(r"\.\s*", flags=re.IGNORECASE)
                house_bill_re = re.compile(r"house bill", flags=re.IGNORECASE)
                senate_bill_re = re.compile(r"senate bill", flags=re.IGNORECASE)

                for bill in bills:
                    bill_id = period_and_whitespace_re.sub("", bill[0])
                    bill_id = house_bill_re.sub("HB", bill_id)
                    bill_id = senate_bill_re.sub("SB", bill_id)

                    # Final step to set correct number of spaces in the id
                    components = component_re.search(bill_id)
                    bill_id = f"{components.group(1)} {int(components.group(2))}"

                    agenda.add_bill(bill_id)

        event.add_source(url)

        yield event

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
