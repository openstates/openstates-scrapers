import datetime
import lxml
import json
import re
import dateutil.parser

from openstates.scrape import Scraper, Event

import pytz


class KSEventScraper(Scraper):
    tz = pytz.timezone("America/Chicago")

    chamber_names = {"upper": "senate", "lower": "house"}

    slug = ""

    # Unlike most states, KS posts most of their hearing data after the date
    # start date defaults to 30 days ago, mostly to cut down on page requests
    # and avoid getting banned by their aggressive anti-scraping code
    def scrape(self, start=None):
        if start is None:
            start = datetime.datetime.now()
            start = start - datetime.timedelta(days=30)
        else:
            start = dateutil.parser.parse(start)

        session = self.latest_session()
        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        self.slug = meta["_scraped_name"]

        com_url = "http://www.kslegislature.org/li/api/v11/rev-1/ctte/"
        coms_page = json.loads(self.get(com_url).content)

        for chamber in ["upper", "lower"]:
            chamber_key = f"{self.chamber_names[chamber]}_committees"
            for com in coms_page["content"][chamber_key]:
                yield from self.scrape_com_page(
                    com["KPID"], chamber, com["TITLE"], start
                )

    def scrape_com_page(self, com_id, chamber, com_name, start):
        # http://www.kslegislature.org/li/b2021_22/committees/ctte_h_agriculture_1/
        com_page_url = (
            f"http://www.kslegislature.org/li/{self.slug}/committees/{com_id}/"
        )

        page = self.get(com_page_url).content
        page = lxml.html.fromstring(page)

        time_loc = page.xpath('//h3[contains(text(), "Meeting Day")]')[0].text_content()

        time = re.search(r"Time:\s(.*)Location", time_loc).group(1).strip()

        location = re.search(r"Location\:(.*)$", time_loc).group(1).strip()

        if location.strip() == "":
            location = "See Agenda"

        doc_page_url = f"http://www.kslegislature.org/li/{self.slug}/committees/{com_id}/documents/"

        page = self.get(doc_page_url).content
        page = lxml.html.fromstring(page)

        for meeting_date in page.xpath('//select[@id="id_date_choice"]/option/@value'):
            meeting_day = dateutil.parser.parse(meeting_date)
            if meeting_day < start:
                continue

            yield from self.scrape_meeting_page(
                com_id, chamber, com_name, meeting_date, time, location
            )

    def scrape_meeting_page(
        self, com_id, chamber, com_name, meeting_date, meeting_time, location
    ):
        # http://www.kslegislature.org/li/b2021_22/committees/ctte_s_jud_1/documents/?date_choice=2021-03-19
        meeting_page_url = (
            f"http://www.kslegislature.org/li/{self.slug}/"
            f"committees/{com_id}/documents/?date_choice={meeting_date}"
        )

        page = self.get(meeting_page_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(meeting_page_url)

        try:
            start_date = dateutil.parser.parse(f"{meeting_date} {meeting_time}")
        except dateutil.parser._parser.ParserError:
            start_date = dateutil.parser.parse(meeting_date)

        start_date = self.tz.localize(start_date)

        pretty_chamber = self.chamber_names[chamber].title()

        event = Event(
            start_date=start_date,
            name=f"{pretty_chamber} {com_name}",
            location_name=location,
        )

        event.add_participant(
            f"{pretty_chamber} {com_name}", type="committee", note="host"
        )

        # Agendas & Minutes
        for row in page.xpath(
            "//table[.//h4[contains(text(), 'Agendas')]]/table[contains(@class,'bottom')]/tbody/tr"
        ):
            doc_name = row.xpath("td[1]")[0].text_content()
            doc_url = row.xpath("td[2]/a/@href")[0]
            event.add_document(doc_name, doc_url, media_type="application/pdf")

        # Witness testimony
        for row in page.xpath("//tr[td[ul[@id='testimony-docs']]]"):

            doc_type = row.xpath("td[1]")[0].text_content()
            meta = row.xpath("td[2]/ul[@id='testimony-docs']")[0]

            witness = meta.xpath("li[strong[contains(text(),'Presenter')]]/text()")[
                0
            ].strip()

            org = ""
            if meta.xpath("li[strong[contains(text(),'Organization')]]/text()"):
                org = meta.xpath("li[strong[contains(text(),'Organization')]]/text()")[
                    0
                ].strip()

            topic = meta.xpath("li[strong[contains(text(),'Topic')]]/text()")[0].strip()

            if org:
                doc_name = f"{doc_type} - {witness} ({org}) - {topic}"
            else:
                doc_name = f"{doc_type} - {witness} - {topic}"

            agenda = event.add_agenda_item(doc_name)
            if meta.xpath("li[strong[contains(text(),'Measure')]]/text()"):
                bill_id = meta.xpath("li[strong[contains(text(),'Measure')]]/text()")[
                    0
                ].strip()
                agenda.add_bill(bill_id)

        event.add_source(meeting_page_url)

        yield event
