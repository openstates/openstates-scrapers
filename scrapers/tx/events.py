from utils import LXMLMixin
import re
import datetime as dt
import dateutil.parser

from openstates.scrape import Scraper, Event

import pytz


class TXEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Central")

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("No session specified; using %s", session)

        if chamber:
            yield from self.scrape_committee_upcoming(session, chamber)
        else:
            yield from self.scrape_committee_upcoming(session, "upper")
            yield from self.scrape_committee_upcoming(session, "lower")

    def scrape_event_page(self, session, chamber, url, datetime):
        page = self.lxmlize(url)
        info = page.xpath("//p")
        metainfo = {}
        plaintext = ""
        for p in info:
            content = re.sub(r"\s+", " ", p.text_content())
            plaintext += content + "\n"
            if ":" in content:
                key, val = content.split(":", 1)
                metainfo[key.strip()] = val.strip()
        committee = metainfo["COMMITTEE"]
        where = metainfo["PLACE"]
        if "CHAIR" in where:
            where, chair = where.split("CHAIR:")
            metainfo["PLACE"] = where.strip()
            metainfo["CHAIR"] = chair.strip()

        chair = None
        if "CHAIR" in metainfo:
            chair = metainfo["CHAIR"]

        plaintext = re.sub(r"\s+", " ", plaintext).strip()
        regexp = r"(S|J|H)(B|M|R) (\d+)"
        bills = re.findall(regexp, plaintext)

        event = Event(
            name=committee, start_date=self._tz.localize(datetime), location_name=where
        )
        event.dedupe_key = url

        event.add_source(url)
        event.add_participant(committee, type="committee", note="host")
        if chair is not None:
            event.add_participant(chair, type="legislator", note="chair")

        # add a single agenda item, attach all bills
        agenda = event.add_agenda_item(plaintext)

        for bill in bills:
            chamber, type, number = bill
            bill_id = "%s%s %s" % (chamber, type, number)
            agenda.add_bill(bill_id)

        yield event

    def scrape_page(self, session, chamber, url):
        page = self.lxmlize(url)
        events = page.xpath("//a[contains(@href, 'schedules/html')]")
        for event in events:
            peers = event.getparent().getparent().xpath("./*")
            date = peers[0].text_content()
            time = peers[1].text_content()
            tad = "%s %s" % (date, time)
            tad = re.sub(r"(PM|AM).*", r"\1", tad)
            if "AM" not in tad and "PM" not in tad:
                tad = date

            datetime = dateutil.parser.parse(tad)

            yield from self.scrape_event_page(
                session, chamber, event.attrib["href"], datetime
            )

    def scrape_upcoming_page(self, session, chamber, url):
        page = self.lxmlize(url)
        date = None
        time = None

        for row in page.xpath(".//tr"):
            title = row.xpath(".//div[@class='sectionTitle']")
            if len(title) > 0:
                date = title[0].text_content()
            time_elem = row.xpath(".//td/strong")
            if time_elem:
                time = time_elem[0].text_content()

            events = row.xpath(".//a[contains(@href, 'schedules/html')]")
            for event in events:

                # Ignore text after the datetime proper (ie, after "AM" or "PM")
                datetime = "{} {}".format(date, time)
                datetime = re.search(r"(?i)(.+?[ap]m).+", datetime)
                if not datetime:
                    self.warning("invalid datetime: %s %s", date, time)
                    continue
                datetime = datetime.group(1)
                datetime = dt.datetime.strptime(datetime, "%A, %B %d, %Y %I:%M %p")

                yield from self.scrape_event_page(
                    session, chamber, event.attrib["href"], datetime
                )

    def scrape_committee_upcoming(self, session, chamber):
        chid = {"upper": "S", "lower": "H", "other": "J"}[chamber]

        url = (
            "https://capitol.texas.gov/Committees/Committees.aspx" + "?Chamber=" + chid
        )

        page = self.lxmlize(url)
        refs = page.xpath("//div[@id='content']//a")
        for ref in refs:
            yield from self.scrape_page(session, chamber, ref.attrib["href"])

        url = (
            "http://capitol.texas.gov/Committees/MeetingsUpcoming.aspx"
            + "?Chamber="
            + chid
        )

        yield from self.scrape_upcoming_page(session, chamber, url)
