from openstates.scrape import Scraper, Event
import lxml
import dateutil.parser
import re
import pytz
from urllib import parse
from dateutil.tz import gettz

from .common import SESSION_SITE_IDS


# NOTE: because of how the bill scraper is imported, this must be run with
# VIRGINIA_FTP_USER="" VIRGINIA_FTP_PASSWORD="" PYTHONPATH=scrapers poetry run os-update va events --scrape
# You don't need a valid u/p for events, the env vars just need to be set.
class VaEventScraper(Scraper):
    _tz = pytz.timezone("America/New_York")
    tzinfos = {"EDT": gettz("America/New_York"), "EST": gettz("America/New_York")}

    def scrape(self, session):
        session_id = SESSION_SITE_IDS[session]

        yield from self.scrape_lower()
        yield from self.scrape_upper(session_id)

    def scrape_lower(self):
        list_url = "https://virginiageneralassembly.gov/house/schedule/meetingSchedule.php?range=long"

        page = self.get(list_url).content
        page = lxml.html.fromstring(page)

        page.make_links_absolute(list_url)

        for row in page.xpath("//table[contains(@class, 'CODayTable')]/tbody/tr"):
            # TODO: it would be nice to go back in and update the record to mark it as cancelled,
            # but since there's no ics link it makes the day logic way more complicated
            if row.xpath(".//span[contains(@class, 'COCancelled')]"):
                continue

            # fallback for unlinked events
            source = "https://virginiageneralassembly.gov/house/schedule/meetingSchedule.php?range=long"

            if row.xpath(".//a[1]/text()"):
                title = row.xpath(".//a[1]/text()")[0].strip()
                source = row.xpath(".//a[1]/@href")[0]
                event_type = "committee-meeting"
            else:
                # skip unlinked misc events
                if row.xpath("td[contains(@class, 'COCommType')]/text()"):
                    title = row.xpath("td[contains(@class, 'COCommType')]/text()")[
                        0
                    ].strip()
                    event_type = "other"
                else:
                    continue

            # cancelled so we lose date/time info
            if not row.xpath(".//a[@title='Add to Calendar']/@href"):
                continue

            date_link = row.xpath(".//a[@title='Add to Calendar']/@href")[0]
            parsed = parse.parse_qs(parse.urlparse(date_link).query)
            date_raw = parsed["dt"][0]
            loc_raw = parsed["loc"][0]
            # Prevent invalid length of location name
            location = loc_raw[:198] if len(loc_raw) > 199 else loc_raw

            start = dateutil.parser.parse(date_raw, tzinfos=self.tzinfos)

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
            event.dedupe_key = f"{title}#{location}#{start}"

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
            summary = row.xpath(".//table/@summary")
            if not summary:
                continue
            summary = summary[0]
            for bill in row.xpath('.//tr[contains(@class, "standardZebra")]/td[1]/a'):
                name = bill.xpath("string()").strip()
                if "Attachment" in summary:
                    url = bill.xpath("@href")[0]
                    agenda.add_media_link(name, url, media_type="application/pdf")
                elif "Block of this committee" in summary:
                    bill_regex = re.compile(r"(HB|HJ|HR|SB|SJ|SR)[0-9]+")
                    if bill_regex.match(name):
                        agenda.add_bill(name)
                    else:
                        raise Exception("Invalid format of Bill ID")
                else:
                    raise Exception("Unknown types of agenda")

    def scrape_upper(self, session_id):
        list_url = f"https://lis.virginia.gov/cgi-bin/legp604.exe?{session_id}+oth+MTG&{session_id}+oth+MTG"
        page = self.get(list_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(list_url)

        date = ""
        time = ""
        # note the [td] at the end, they have some empty tr-s so skip them
        for row in page.xpath("//div[@id='mainC']/center/table//tr[td]"):
            if row.xpath("td[1]/text()")[0].strip() != "":
                date = row.xpath("td[1]/text()")[0].strip()

            time_col = row.xpath("td[2]/text()")[0]
            status = "tentative"
            if "cancelled" in time_col.lower():
                status = "cancelled"
            if "a.m." in time_col or "p.m." in time_col:
                time = time_col.replace("a.m.", "am").replace("p.m.", "pm").strip()

            when = dateutil.parser.parse(f"{date} {time}".strip())
            when = self._tz.localize(when)

            description = row.xpath("td[3]")[0].xpath("string()")
            description = " ".join(description.split()).strip()

            # location is generally everything after the semicolon in the description
            # it is sometimes the thing after colon in description
            # removes these strings "- 1/2 hour, - 2 hours, - 30 minutes, - Immediately, (...)" in the description
            desc_split = re.split(
                r"(?:\:|;|\(|\)|-[\s\d\/\.]+(?:hour(?:s)?|minute(?:s)?|Immediately))",
                description,
            )
            if len(desc_split) > 1:
                loc_raw = desc_split[1].strip()
                # Prevent invalid length of location name
                location = loc_raw[:198] if len(loc_raw) > 199 else loc_raw
            else:
                location = "Unknown"

            event = Event(
                name=description,
                start_date=when,
                classification="committee-meeting",
                location_name=location,
                status=status,
            )
            event.add_source(list_url)

            # committee info & sub-committee info urls
            committee_info_xpath = row.xpath(
                './/a[contains(., "committee info")]/@href'
            )
            # for senate only.
            if "Senate" in description and committee_info_xpath:
                committee_url = committee_info_xpath[0]
                if "lis.virginia.gov" in committee_url:
                    self.scrape_upper_com(event, committee_url)

            yield event

    def scrape_upper_com(self, event, url):
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        # add members
        for person in (
            page.xpath('//div[@id="mainC"]/p[./a[contains(@href, "mbr")]]')[0]
            .xpath("string()")
            .split(",")
        ):
            event.add_participant(
                person.split("(")[0].strip(),
                type="person",
                note=person.split("(")[1].strip(") ").lower()
                if "(" in person
                else "member",
            )

        # add committee name
        committee_name = (
            page.xpath('//div[@id="mainC"]/h3[@class="xpad"]')[0]
            .xpath("string()")
            .replace("\n", "")
            .strip()
        )
        event.add_participant(committee_name, type="committee", note="host")
        # get the url for only event date
        event_dt = event.start_date.strftime("%B %d")
        # the url contains +com+ for committee.
        if "com" in url:
            # click committee dockets (only 1 url). used "for" statement to avoid exception.
            for doc_url in page.xpath('//a[contains(@href, "DOC")]/@href'):
                doc_page = self.get(doc_url).content
                page = lxml.html.fromstring(doc_page)
                page.make_links_absolute(url)
        # click dockets for the current event date. only 1 url if exists.
        for url in page.xpath(f'//a[contains(., "{event_dt}")]/@href'):
            event.add_document("Agenda", url, media_type="text/html")
            self.scrape_upper_agenda(event, url)

    def scrape_upper_agenda(self, event, url):
        # scrape agenda title and bill ids
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        title = " ".join(
            [sub_title.xpath("string()") for sub_title in page.xpath("//center/b")]
        )
        agenda = event.add_agenda_item(title)
        for row in page.xpath("//p[./b/b/a/@href]"):
            bill = "".join(row.xpath("./b/b/a/text()")[0].replace(".", "").split())
            bill_regex = re.compile(r"(HB|HJ|HR|SB|SJ|SR)[0-9]+")
            if bill_regex.match(bill):
                agenda.add_bill(bill)
