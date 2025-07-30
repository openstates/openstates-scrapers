import dateutil.parser
from dateutil.parser import ParserError
import functools
import lxml
import pytz
import re

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


class KYEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    def scrape(self):
        self.headers[
            "User-Agent"
        ] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
        url = "https://apps.legislature.ky.gov/legislativecalendar"

        page = self.get(url, verify=False).content
        page = lxml.html.fromstring(page)

        if len(page.xpath('//div[contains(@class,"TimeAndLocation")]')) == 0:
            raise EmptyScrape
        event_count = 0
        events = set()

        for time_row in page.xpath('//div[contains(@class,"TimeAndLocation")]'):
            date = (
                time_row.xpath(
                    'preceding-sibling::div[contains(@class,"DateHeading")][1]'
                )[0]
                .text_content()
                .strip()
            )

            status = "tentative"

            if time_row.xpath('div[contains(@class,"Cancelled")]'):
                status = "cancelled"

            row_text = time_row.text_content()
            row_text = row_text.replace("Noon", "PM")
            # upon (Recess|Adj.) (of) (the) (House|Senate)
            row_text = re.sub(
                r"Upon (Recess|Adj\.)\s*(of)?\s*(the)?\s*(House|Senate)?", "", row_text
            )
            parts = re.split(r",|AM|PM", row_text)
            time = parts[0].strip()
            location = " ".join(x.replace(r"\xa0", "").strip() for x in parts[1:])

            when = f"{date} {time}"
            try:
                when = dateutil.parser.parse(when)
            except ParserError:
                self.warning(
                    f"Unable to parse {when}, trying date without time component"
                )
                when = dateutil.parser.parse(date)

            when = self._tz.localize(when)

            if not time_row.xpath(
                'following-sibling::div[contains(@class,"CommitteeName")][1]/a'
            ):
                continue

            com_name = (
                time_row.xpath(
                    'following-sibling::div[contains(@class,"CommitteeName")][1]/a'
                )[0]
                .text_content()
                .strip()
            )
            event_name = f"{com_name}#{location}#{when}"
            if event_name in events:
                self.warning(f"Duplicate event: {event_name}")
                continue
            events.add(event_name)
            event = Event(
                name=com_name,
                start_date=when,
                classification="committee-meeting",
                location_name=location,
                status=status,
            )
            event.dedupe_key = event_name
            if time_row.xpath('following-sibling::div[contains(@class,"Agenda")][1]'):
                agenda_row = time_row.xpath(
                    'following-sibling::div[contains(@class,"Agenda")][1]'
                )[0]
                agenda_text = agenda_row.text_content().strip()

                agenda = event.add_agenda_item(agenda_text)

                for bill_link in agenda_row.xpath('.//a[contains(@href,"/record/")]'):
                    agenda.add_bill(bill_link.text_content().strip())

            event.add_participant(com_name, note="host", type="committee")

            com_page_link = time_row.xpath(
                'following-sibling::div[contains(@class,"CommitteeName")][1]/a/@href'
            )[0].replace(" ", "+")

            docs = self.scrape_com_docs(com_page_link)
            lookup_date = when.strftime("%Y-%m-%d")

            if lookup_date in docs["mats"]:
                for mat in docs["mats"][lookup_date]:
                    event.add_document(mat["text"], mat["url"], on_duplicate="ignore")

            if "minutes" in docs and lookup_date in docs["minutes"]:
                for mat in docs["minutes"][lookup_date]:
                    event.add_document(mat["text"], mat["url"], on_duplicate="ignore")

            event.add_source(url)

            event_count += 1
            yield event

        if event_count < 1:
            raise EmptyScrape

    @functools.lru_cache(maxsize=None)
    def scrape_com_docs(self, url):
        page = self.get(url, verify=False).content
        page = lxml.html.fromstring(page)

        docs = {}

        if page.xpath('//a[contains(text(), "Meeting Materials")]/@href'):
            mats_link = page.xpath('//a[contains(text(), "Meeting Materials")]/@href')[
                0
            ]
            docs["mats"] = self.scrape_meeting_mats(mats_link)

        if page.xpath('//a[contains(text(), "Minutes")]/@href'):
            minutes_link = page.xpath('//a[contains(text(), "Minutes")]/@href')[0]
            docs["minutes"] = self.scrape_minutes(minutes_link)

        return docs

    def scrape_meeting_mats(self, url):
        page = self.get(url, verify=False).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        docs = {}
        for header in page.xpath(
            '//div[h2[contains(text(), "Meeting Materials")]]/div[1]/h3'
        ):
            date_text = header.text_content().strip()

            if "Other Meeting" in date_text:
                continue

            if "No documents available" in date_text:
                continue

            when = dateutil.parser.parse(date_text)

            lookup_date = when.strftime("%Y-%m-%d")

            if lookup_date not in docs:
                docs[lookup_date] = []

            for doc_link in header.xpath("following::ul[1]/li/a"):
                docs[lookup_date].append(
                    {
                        "url": doc_link.xpath("@href")[0],
                        "text": doc_link.text_content().strip(),
                    }
                )

        return docs

    def scrape_minutes(self, url):
        page = self.get(url, verify=False).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        docs = {}
        for link in page.xpath('//a[contains(@href, "/minutes/")]'):
            when = dateutil.parser.parse(link.text_content())
            lookup_date = when.strftime("%Y-%m-%d")

            if lookup_date not in docs:
                docs[lookup_date] = []

            if link.xpath("@href"):
                docs[lookup_date].append(
                    {"url": link.xpath("@href")[0], "text": "Minutes"}
                )
        return docs
