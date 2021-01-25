from openstates.scrape import Scraper, Event
import lxml
import dateutil.parser
import re
import pytz
from urllib import parse

from .common import SESSION_SITE_IDS


# NOTE: because of how the bill scraper is imported, this must be run with
# VIRGINIA_FTP_USER="" VIRGINIA_FTP_PASSWORD="" PYTHONPATH=scrapers poetry run os-update va events --scrape
# You don't need a valid u/p for events, the env vars just need to be set.
class VaEventScraper(Scraper):
    # chambers = {"lower": "House", "upper": "Senate", "joint": "Joint"}
    chamber_codes = {"H": "lower", "S": "upper", "J": "joint"}
    _tz = pytz.timezone("America/New_York")

    def scrape(self):
        session = self.latest_session()
        session_id = SESSION_SITE_IDS[session]

        # yield from self.scrape_lower()
        yield from self.scrape_upper(session_id)

    def scrape_lower(self):
        list_url = (
            "https://virginiageneralassembly.gov/house/schedule/meetingSchedule.php"
        )

        page = self.get(list_url).content
        page = lxml.html.fromstring(page)

        page.make_links_absolute(list_url)

        for row in page.xpath("//table[contains(@class, 'CODayTable')]/tbody/tr"):

            # TODO: it would be nice to go back in and update the record to mark it as cancelled,
            # but since there's no ics link it makes the day logic way more complicated
            if row.xpath(".//span[contains(@class, 'COCancelled')]"):
                continue

            # fallback for unlinked events
            source = (
                "https://virginiageneralassembly.gov/house/schedule/meetingSchedule.php"
            )

            if row.xpath(".//a[1]/text()"):
                title = row.xpath(".//a[1]/text()")[0].strip()
                source = row.xpath(".//a[1]/@href")[0]
                event_type = "committee-meeting"
            else:
                title = row.xpath("td[contains(@class, 'COCommType')]/text()")[
                    0
                ].strip()
                event_type = "other"

            print(title)

            date_link = row.xpath(".//a[@title='Add to Calendar']/@href")[0]
            parsed = parse.parse_qs(parse.urlparse(date_link).query)
            date_raw = parsed["dt"][0]
            location = parsed["loc"][0]
            print(date_raw)

            start = dateutil.parser.parse(date_raw)
            print(start)
            print(location)

            # If there's a chair in parentheticals, remove them from the title
            # and add as a person instead
            chair_note = re.findall(r"\(.*\)", title)
            chair = None
            for chair_str in chair_note:
                title = title.replace(chair_str, "").strip()
                # drop the outer parens
                chair = chair_str[1:-1]

            event = Event(
                name=title,
                start_date=start,
                location_name=location,
                classification=event_type,
            )
            event.add_source(source)

            if chair is not None:
                event.add_participant(chair, type="person", note="chair")

            if event_type == "committee-meeting":
                event.add_participant(title, type="committee", note="host")

            if row.xpath(".//a[contains(@class,'COAgendaLink')]"):
                agenda_url = row.xpath(".//a[contains(@class,'COAgendaLink')]/@href")[0]
                event.add_document("Agenda", agenda_url, media_type="text/html")
                self.scrape_lower_agenda(event, agenda_url)

            yield event

    def scrape_lower_agenda(self, event, url):
        page = self.get(url).content
        page = lxml.html.fromstring(page)

        page.make_links_absolute(url)

        if page.xpath(
            '//tr[td[contains(@class,"agendaLabel") and contains(text(), "Notes")]]/td[2]'
        ):
            note = page.xpath(
                '//tr[td[contains(@class,"agendaLabel") and contains(text(), "Notes")]]/td[2]/text()'
            )[0].strip()
            event.add_agenda_item(note)

        for row in page.xpath('//div[contains(@class,"agendaContainer")]'):
            title = row.xpath(
                './/span[contains(@class,"reportBlockContainerCon")]/h2/text()'
            )[0].strip()
            agenda = event.add_agenda_item(title)

            for bill in row.xpath(
                './/tr[contains(@class, "standardZebra")]/td[1]/a/text()'
            ):
                agenda.add_bill(bill)

        #             event.add_document(
        #                 meeting_doc["Title"],
        #                 meeting_doc_url,
        #                 media_type="application/pdf",
        #             )

        #         event.add_source(
        #             f"https://sdlegislature.gov/Session/Committee/{com['SessionCommitteeId']}/Detail"
        #         )

        #     a = event.add_agenda_item(description=bill_number)
        #     a.add_bill(bill_number)

    def scrape_upper(self, session_id):
        list_url = f"https://lis.virginia.gov/cgi-bin/legp604.exe?{session_id}+oth+MTG&{session_id}+oth+MTG"
        page = self.get(list_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(list_url) 

        date = None
        # note the [td] at the end, they have some empty tr-s so skip them
        for row in page.xpath("//div[@id='mainC']/center/table/tr[td]"):
            print("row")
            if row.xpath('td[1]/text()')[0].strip() != '':
                date = row.xpath('td[1]/text()')[0].strip()

            description = row.xpath('td[3]/text()')[0].strip()
            print(description)

            # data on the house page is better
            if 'senate' not in description.lower():
                continue

            time = row.xpath('td[2]/text()')[0].strip()

            try:
                when = dateutil.parser.parse(f"{date} {time}")
            except dateutil.parser._parser.ParserError:
                when = dateutil.parser.parse(date)

            when = self._tz.localize(when)

            print(description)
            print(when)
            event = Event(
                name=description,
                start_date=when,
                classification="committee-meeting",
                location_name="TODO"
            )

            event.add_source(list_url)
            yield event
