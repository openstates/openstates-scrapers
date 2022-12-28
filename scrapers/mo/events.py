import pytz
import lxml
import dateutil.parser
import re

from utils import LXMLMixin
from utils.events import match_coordinates
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


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

            location = "{}, {}".format(
                location, "201 W Capitol Ave, Jefferson City, MO 65101"
            )

            if not page.xpath(
                '//td[descendant::b[contains(text(),"Committee")]]/a/text()'
            ):
                continue

            com = page.xpath(
                '//td[descendant::b[contains(text(),"Committee")]]/a/text()'
            )[0]
            com = com.split(", Senator")[0].strip()

            try:
                start_date = dateutil.parser.parse(f"{when_date} {when_time}")
            except dateutil.parser._parser.ParserError:
                start_date = dateutil.parser.parse(when_date)

            start_date = self._TZ.localize(start_date)

            event = Event(
                start_date=start_date,
                name=com,
                location_name=location,
                classification="committee-meeting",
            )

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
                    agenda_item.add_bill(bill_link)
                else:
                    agenda_line = bill_table.xpath("string(tr[1])").strip()
                    agenda_item = event.add_agenda_item(description=agenda_line)

            yield event

    def scrape_lower(self):
        listing_url = "https://house.mo.gov/HearingsTimeOrder.aspx"

        html = self.get(listing_url).text

        # The HTML here isn't wrapped in a container per-event
        # which makes xpath a pain. So string split by <hr>
        # then parse each event's fragment for cleaner results
        for fragment in html.split("<hr />")[1:]:
            page = lxml.html.fromstring(fragment)

            # Skip date header rows
            if page.xpath('//div[@id="DateGroup"]'):
                continue
            else:
                yield from self.scrape_lower_item(page)

    def scrape_lower_item(self, page):
        # print(lxml.etree.tostring(page, pretty_print=True))
        com = self.table_row_content(page, "Committee:")
        when_date = self.table_row_content(page, "Date:")
        when_time = self.table_row_content(page, "Time:")
        location = self.table_row_content(page, "Location:")

        if "house hearing room" in location.lower():
            location = "{}, {}".format(
                location, "201 W Capitol Ave, Jefferson City, MO 65101"
            )

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

        event = Event(
            start_date=start_date,
            name=com,
            location_name=location,
            classification="committee-meeting",
        )

        event.add_source("https://house.mo.gov/HearingsTimeOrder.aspx")

        event.add_participant(com, type="committee", note="host")

        # different from general MO link xpath due to the <b>
        house_link_xpath = (
            './/a[contains(@href, "Bill.aspx") '
            'or contains(@href, "bill.aspx")]/b/text()'
        )

        match_coordinates(
            event,
            {
                "201 W Capitol Ave": (38.57918, -92.17306),
            },
        )

        for bill_title in page.xpath(house_link_xpath):
            bill_no = bill_title.split("--")[0].strip()
            bill_no = bill_no.replace("HCS", "").strip()

            agenda_item = event.add_agenda_item(description=bill_title)
            agenda_item.add_bill(bill_no)

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

    def table_row_content(self, page, header):
        content = page.xpath(
            'string(.//tr[td[contains(string(.), "{}")]]/td[2])'.format(header)
        )
        if len(content) > 0:
            return content.strip()
        else:
            return ""
