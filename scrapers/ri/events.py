import re
import datetime
import dateutil

import pytz
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

from utils import LXMLMixin


agenda_url = "https://status.rilegislature.gov/agendas.aspx"
column_order = {"upper": 1, "joint": 2, "lower": 0}

replace = {
    "House Joint Resolution No.": "HJR ",
    "House Resolution No.": "HR ",
    "House Bill No.": "HB ",
    "Senate Joint Resolution No.": "SJR ",
    "Senate Resolution No.": "SR ",
    "Senate Bill No.": "SB ",
    "\xa0": " ",
    "\u00a0": " ",
    "SUB A": "",
    "SUB A as amended": "",
    "PROPOSED SUBSTITUTE": "",
}


class RIEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Eastern")
    found_events = False

    def scrape_agenda(self, chamber, url, event_keys):
        status = "tentative"
        page = self.lxmlize(url)
        # Get the date/time info:
        date_time = page.xpath("//table[@class='time_place']")
        if not date_time:
            return

        date_time = date_time[0]
        lines = date_time.xpath("./tr")
        metainf = {}
        for line in lines:
            tds = line.xpath("./td")
            metainf[tds[0].text_content()] = tds[1].text_content()
        date = metainf["DATE:"]
        time = metainf["TIME:"]
        where = metainf["PLACE:"]

        # check for duration in time
        if " - " in time:
            start, end = time.split(" - ")
            am_pm_srch = re.search("(?i)(am|pm)", end)
            if am_pm_srch:
                time = " ".join([start, am_pm_srch.group().upper()])
            else:
                time = start

        event_desc = "Meeting Notice"
        if "Rise" in time:
            when = date
            event_desc = "Meeting Notice: Starting at {}".format(time)
        else:
            when = "%s %s" % (date, time)
        if "CANCELLED" in when.upper() or "CANCELED" in when.upper():
            status = "cancelled"

        if "POSTPONED" in when.upper():
            status = "cancelled"

        if page.xpath("//span[@id='lblSession']"):
            event_desc = (
                page.xpath("//span[@id='lblSession']")[0].text_content().strip()
            )

        when = dateutil.parser.parse(when, fuzzy=True)

        if when.time() == datetime.time(0, 0):
            when = when.date()
        else:
            when = self._tz.localize(when)

        # Unique key to prevent triggering of DuplicateItemError during import,
        #  so duplication check can be conducted below instead
        event_details_key = f"{chamber}#{event_desc}#{when}#{where}"

        if event_details_key in event_keys:
            self.warning(f"Skipping duplicate event: {event_details_key}")
            return
        else:
            event_keys.add(event_details_key)

        event = Event(
            name=event_desc, start_date=when, location_name=where, status=status
        )
        event.dedupe_key = event_details_key
        url = url.replace("http:", "https:")
        event.add_document("Agenda", url, media_type="text/html", on_duplicate="ignore")
        event.add_source(url)

        # aight. Let's get us some bills!
        bills = page.xpath("//b/a")
        for bill in bills:
            bill_ft = bill.attrib["href"]
            bill_ft = bill_ft.replace("http:", "https:")
            event.add_document(
                bill.text_content(),
                bill_ft,
                media_type="application/pdf",
                on_duplicate="ignore",
            )

            root_elements = bill.xpath("../../*")
            root = []
            for e in root_elements:
                # The first bill listed is in the same <td> as the page header,
                # which includes the "SCHEDULED FOR" text. This would cause the
                # first bill to be skipped unless we omit it here.
                if (
                    e.tag == "b"
                    and len(e.getchildren()) == 1
                    and e.getchildren()[0].tag == "u"
                ):
                    continue
                # Add the rest of the text normally
                root.append(e.text_content())

            bill_id = "".join(root).replace("\u00a0", "")

            if "SCHEDULED FOR" in bill_id:
                continue

            for thing in replace:
                bill_id = bill_id.replace(thing, replace[thing])

            item = event.add_agenda_item(bill_id)
            item.add_bill(bill_id)

        # sometimes bill references are just plain links or plain text.
        bill_links = page.xpath('//a[contains(@href,"/BillText/")]/@href')
        linked_bills = set()

        bill_id_re = re.compile(r"\/([a-z]+)(\d+)\.pdf", flags=re.IGNORECASE)
        for bill_link in bill_links:
            bill_nums = bill_id_re.findall(bill_link)
            for chamber, bill_num in bill_nums:
                # Bill PDFs don't include the "B" in "HB" or "SB", so it must be added
                bill = f"{chamber}B {int(bill_num)}"
                linked_bills.add(bill)

        # sometimes (H 1234) ends up in the title or somewhere else unlinked
        text_bills = re.findall(
            r"\(([a-z]{1,3})\s?(\d+)\)", page.text_content(), flags=re.IGNORECASE
        )
        for bill_str, bill_num in text_bills:
            bill = f"{bill_str} {bill_num}"
            linked_bills.add(bill)

        if len(linked_bills) != 0:
            item = event.add_agenda_item("Bills under consideration")
            for bill in linked_bills:
                item.add_bill(bill)

        if page.xpath("//span[@id='lblSession']"):
            committee = page.xpath("//span[@id='lblSession']")[0].text_content()
            event.add_participant(committee, "committee", note="host")

        self.found_events = True

        yield event

    def scrape_agenda_dir(self, chamber, url, event_keys):
        page = self.lxmlize(url)
        rows = page.xpath("//table[@class='agenda_table']/tr")[1:]
        for row in rows:
            url = row.xpath("./td")[-1].xpath(".//a")[0]
            yield from self.scrape_agenda(chamber, url.attrib["href"], event_keys)

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower", "joint"]
        event_keys = set()
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, event_keys)
        if not self.found_events:
            raise EmptyScrape

    def scrape_chamber(self, chamber, event_keys):
        offset = column_order[chamber]
        page = self.lxmlize(agenda_url)
        rows = page.xpath("//table[@class='agenda_table']/tr")[1:]
        for row in rows:
            ctty = row.xpath("./td")[offset]
            to_scrape = ctty.xpath("./a")
            for page in to_scrape:
                yield from self.scrape_agenda_dir(
                    chamber, page.attrib["href"], event_keys
                )
