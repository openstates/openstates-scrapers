import re
import datetime as dt

import pytz
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

from utils import LXMLMixin


agenda_url = "http://status.rilin.state.ri.us/agendas.aspx"
column_order = {"upper": 1, "other": 2, "lower": 0}

replace = {
    "House Joint Resolution No.": "HJR",
    "House Resolution No.": "HR",
    "House Bill No.": "HB",
    "Senate Joint Resolution No.": "SJR",
    "Senate Resolution No.": "SR",
    "Senate Bill No.": "SB",
    "\xa0": " ",
    "\u00a0": " ",
    "SUB A": "",
    "SUB A as amended": "",
    "PROPOSED SUBSTITUTE": "",
}


class RIEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Eastern")
    found_events = False

    def scrape_agenda(self, chamber, url):
        page = self.lxmlize(url)
        # Get the date/time info:
        date_time = page.xpath("//table[@class='time_place']")
        if date_time == []:
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

        fmts = ["%A, %B %d, %Y", "%A, %B %d, %Y %I:%M %p", "%A, %B %d, %Y %I:%M"]

        event_desc = "Meeting Notice"
        if "Rise" in time:
            datetime = date
            event_desc = "Meeting Notice: Starting at {}".format(time)
        else:
            datetime = "%s %s" % (date, time)
        if "CANCELLED" in datetime.upper() or "CANCELED" in datetime.upper():
            return

        if page.xpath("//span[@id='lblSession']"):
            event_desc = (
                page.xpath("//span[@id='lblSession']")[0].text_content().strip()
            )

        transtable = {
            "P.M": "PM",
            "PM.": "PM",
            "P.M.": "PM",
            "A.M.": "AM",
            "POSTPONED": "",
            "RESCHEDULED": "",
            "and Rise of the Senate": "",
        }
        for trans in transtable:
            datetime = datetime.replace(trans, transtable[trans])

        datetime = datetime.strip()

        for fmt in fmts:
            try:
                datetime = dt.datetime.strptime(datetime, fmt)
                break
            except ValueError:
                continue

        event = Event(
            name=event_desc, start_date=self._tz.localize(datetime), location_name=where
        )

        event.add_document("Agenda", url, media_type="text/html", on_duplicate="ignore")
        event.add_source(url)

        # aight. Let's get us some bills!
        bills = page.xpath("//b/a")
        for bill in bills:
            bill_ft = bill.attrib["href"]
            event.add_document(
                bill.text_content(),
                bill_ft,
                media_type="application/pdf",
                on_duplicate="ignore",
            )
            root = bill.xpath("../../*")
            root = [x.text_content() for x in root]
            bill_id = "".join(root).replace("\u00a0", "")

            if "SCHEDULED FOR" in bill_id:
                continue

            descr = bill.getparent().getparent().text_content().replace("\u00a0", " ")

            for thing in replace:
                bill_id = bill_id.replace(thing, replace[thing])

            item = event.add_agenda_item(descr)
            item.add_bill(bill_id)

        # sometimes bill references are just plain links or plain text.
        bill_links = page.xpath('//a[contains(@href,"/BillText/")]/@href')
        linked_bills = set()
        for bill_link in bill_links:
            bill_nums = re.findall(r"\/(\w+\d+)\.pdf", bill_link, flags=re.IGNORECASE)
            for bill_num in bill_nums:
                linked_bills.add(bill_num)

        # sometimes (H 1234) ends up in the title or somewhere else unlinked
        text_bill_nums = re.findall(
            r"\((\w{1,3}\s?\d+)\)", page.text_content(), flags=re.IGNORECASE
        )
        for bill_num in text_bill_nums:
            bill_num = bill_num.replace(" ", "")
            linked_bills.add(bill_num)

        if len(linked_bills) != 0:
            item = event.add_agenda_item("Bills under consideration")
            for bill in linked_bills:
                item.add_bill(bill)

        if page.xpath("//span[@id='lblSession']"):
            committee = page.xpath("//span[@id='lblSession']")[0].text_content()
            event.add_participant(committee, "committee", note="host")

        self.found_events = True
        yield event

    def scrape_agenda_dir(self, chamber, url):
        page = self.lxmlize(url)
        rows = page.xpath("//table[@class='agenda_table']/tr")[1:]
        for row in rows:
            url = row.xpath("./td")[-1].xpath(".//a")[0]
            yield from self.scrape_agenda(chamber, url.attrib["href"])

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        offset = column_order[chamber]
        page = self.lxmlize(agenda_url)
        rows = page.xpath("//table[@class='agenda_table']/tr")[1:]
        for row in rows:
            ctty = row.xpath("./td")[offset]
            to_scrape = ctty.xpath("./a")
            for page in to_scrape:
                yield from self.scrape_agenda_dir(chamber, page.attrib["href"])

        if not self.found_events:
            raise EmptyScrape
