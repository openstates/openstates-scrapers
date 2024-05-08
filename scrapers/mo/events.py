import pytz
import lxml
import dateutil.parser
import re

from utils import LXMLMixin
from utils.events import match_coordinates
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


class UnknownBillStringPattern(BaseException):
    def __init__(self, bill_string):
        super().__init__(
            "Char '&' present in string but known bill id patterns not found."
            f" Bill string: '{bill_string}'"
        )


# Regex pattern for extracting multiple bill ids
#  ex. "HJRs 33 & 45" or "HBs 882 & 518"
multi_bills_re = re.compile(
    r"(SJR|SRB|HCR|HB|HR|SRM|SCR|SB|HRM|HCB|HJR|SM|HRB|HEC|GRP|HC|SR)s*\s+(\d+)"
)


def add_bill_to_agenda(agenda_item, bill_text):
    """
    Helper func adds bills from text that may contain one or multiple bills.
    ex. "SB 123" or "SBs 123 & 341"
    """
    # Start by assuming there's only one bill in string
    item_bills = [bill_text]

    # Multiple bills detected
    if "&" in bill_text:
        multi_bill_match = multi_bills_re.search(bill_text)
        if multi_bill_match:
            prefix, raw_bill_nums = multi_bill_match.groups()
            raw_bill_nums_list = raw_bill_nums.split()
            item_bills = []
            for raw_str in raw_bill_nums_list:
                num_match = re.search(r"(\d+)", raw_str)
                if num_match:
                    bill_num = num_match.group(1)
                    item_bills.append(f"{prefix} {bill_num}")
        # If regex pattern does not cover particular case of '&' in string
        else:
            raise UnknownBillStringPattern(bill_text)

    # Add all bills
    for bill in item_bills:
        agenda_item.add_bill(bill)


class MOEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("America/Chicago")
    bill_link_xpath = (
        './/a[contains(@href, "Bill.aspx") ' 'or contains(@href, "bill.aspx")]/text()'
    )

    def scrape(self, chamber=None):
        event_count = 0
        if chamber is None:
            for chamber in ["upper", "lower"]:
                for event in self.scrape_chamber(chamber):
                    event_count += 1
                    yield event
        else:
            for event in self.scrape_chamber(chamber):
                event_count += 1
                yield event

        if event_count < 1:
            raise EmptyScrape

    def scrape_chamber(self, chamber):
        if chamber == "upper":
            yield from self.scrape_upper()
        elif chamber == "lower":
            yield from self.scrape_lower()

    def scrape_upper(self):
        listing_url = "https://www.senate.mo.gov/hearingsschedule/hrings.htm"

        html = self.get(listing_url).text
        events = set()

        # The HTML here isn't wrapped in a container per-event
        # which makes xpath a pain. So string split by <hr>
        # then parse each event's fragment for cleaner results
        for fragment in html.split("<hr />")[1:]:
            page = lxml.html.fromstring(fragment)

            when_date = self.row_content(page, "Date:")
            when_time = self.row_content(page, "Time:")
            when_time = re.sub("or upon .* recess", "", when_time)

            # fix for upon adjournment
            when_time = when_time.replace(
                "or upon morning adjournment whichever is later", ""
            ).strip()
            # 15/30/45 minutes/hours upon adjournment/recess
            when_time = re.sub(r"\d+ \w+ upon \w+", "", when_time, flags=re.IGNORECASE)
            # a.m. and p.m. seem to confuse dateutil.parser
            when_time = when_time.replace("A.M.", "AM").replace("P.M.", "PM")

            location = self.row_content(page, "Room:")

            location = f"{location}, 201 W Capitol Ave, Jefferson City, MO 65101"

            if not page.xpath('//td//b[contains(text(),"Committee")]/a/text()'):
                continue

            com = page.xpath('//td//b[contains(text(),"Committee")]/a/text()')[0]
            com = com.split(", Senator")[0].strip()

            try:
                start_date = dateutil.parser.parse(f"{when_date} {when_time}")
            except dateutil.parser._parser.ParserError:
                start_date = dateutil.parser.parse(when_date)

            start_date = self._TZ.localize(start_date)
            event_name = f"Upper#{com}#{location}#{start_date}"
            if event_name in events:
                self.warning(f"Duplicate event {event_name}")
                continue
            events.add(event_name)
            event = Event(
                start_date=start_date,
                name=com,
                location_name=location,
                classification="committee-meeting",
            )
            event.dedupe_key = event_name
            event.add_source(listing_url)

            event.add_participant(com, type="committee", note="host")

            match_coordinates(
                event,
                {
                    "201 W Capitol Ave": (38.57918, -92.17306),
                },
            )

            for bill_table in page.xpath('//table[@width="85%" and @border="0"]'):
                bill_link = ""
                if bill_table.xpath(self.bill_link_xpath):
                    agenda_line = bill_table.xpath("string(tr[2])").strip()
                    agenda_item = event.add_agenda_item(description=agenda_line)

                    bill_link = bill_table.xpath(self.bill_link_xpath)[0].strip()
                    add_bill_to_agenda(agenda_item, bill_link)
                else:
                    agenda_line = bill_table.xpath("string(tr[1])").strip()
                    agenda_item = event.add_agenda_item(description=agenda_line)

            yield event

    def scrape_lower(self):
        headers = {
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Referer": "https://documents.house.mo.gov/",
            "sec-ch-ua-mobile": "?0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "sec-ch-ua-platform": '"Windows"',
        }
        response = self.get(
            "https://documents.house.mo.gov/SessionSet.js?v=2", headers=headers
        )
        session_code_re = re.compile(r"sessionyearcode = '(\d+)'")
        session_code = session_code_re.search(response.text).group(1)

        listing_xml_url = (
            f"https://documents.house.mo.gov/xml/{session_code}-UpcomingHearingList.XML"
        )

        xml_content = self.get(listing_xml_url).text
        tree = lxml.html.fromstring(xml_content)

        events = set()
        for hearing in tree.xpath("//hearinginfo"):
            for item in self.scrape_lower_item(hearing):
                if item.dedupe_key in events:
                    self.warning(f"Skipping duplicate event: {item.dedupe_key}")
                    continue
                events.add(item.dedupe_key)
                yield item

    def scrape_lower_item(self, page):
        com = page.xpath("./committeename/text()")[0]
        when_date = page.xpath("./hearingdate/text()")[0]
        when_time = page.xpath("./hearingtime/text()")[0]
        location = page.xpath("./hearinglocation/text()")[0]

        if "house hearing room" in location.lower():
            location = f"{location}, 201 W Capitol Ave, Jefferson City, MO 65101"

        # fix some broken times, e.g. '12 :00'
        when_time = when_time.replace(" :", ":")
        # a.m. and p.m. seem to confuse dateutil.parser
        when_time = when_time.replace("A.M.", "AM").replace("P.M.", "PM")

        # some times have extra info after the AM/PM
        if "upon" in when_time:
            when_time = when_time.split("AM", 1)[0]
            when_time = when_time.split("PM", 1)[0]

        # fix '- Upcoming', '- In Progress'  in dates
        when_date = re.sub(r"- (.*)", "", when_date).strip()

        try:
            start_date = dateutil.parser.parse(f"{when_date} {when_time}")
        except dateutil.parser._parser.ParserError:
            start_date = dateutil.parser.parse(when_date)

        start_date = self._TZ.localize(start_date)
        event_name = f"Lower#{com}#{location}#{start_date}"

        event = Event(
            start_date=start_date,
            name=com,
            location_name=location,
            classification="committee-meeting",
        )
        event.dedupe_key = event_name
        event.add_source("https://house.mo.gov/HearingsTimeOrder.aspx")

        event.add_participant(com, type="committee", note="host")

        match_coordinates(
            event,
            {
                "201 W Capitol Ave": (38.57918, -92.17306),
            },
        )

        for bill in page.xpath("./hearingbills/hearingbill"):
            bill_no = bill.xpath("./currentbillstring/text()")[0]
            bill_no = bill_no.replace("HCS", "").strip()

            if bill.xpath("./shorttitle/text()"):
                bill_title = bill.xpath("./shorttitle/text()")[0]
            else:
                bill_title = bill_no

            agenda_item = event.add_agenda_item(description=bill_title)
            add_bill_to_agenda(agenda_item, bill_no)

        yield event

    # Given <td><b>header</b> other text</td>,
    # return 'other text'
    def row_content(self, page, header):
        content = page.xpath(
            '//td[descendant::b[contains(text(),"{}")]]/text()'.format(header)
        )
        if len(content) > 0:
            return content[0].strip()
        else:
            return ""
