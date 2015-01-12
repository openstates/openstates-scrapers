import re
import datetime as dt

from billy.scrape.events import EventScraper, Event
from openstates.utils import LXMLMixin

import pytz
import lxml.html

pages = {
    "lower" : "http://www.legislature.state.oh.us/house_committee_schedule.cfm"
}

class OHEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'oh'

    _tz = pytz.timezone('US/Eastern')

    def scrape_page(self, chamber, session):
        url = pages[chamber]
        page = self.lxmlize(url)

        rows = page.xpath("//table[@class='MsoNormalTable']/tr")
        header = rows[0]
        rows = rows[1:]

        week_of = page.xpath("//h3[@align='center']/b/text()")[0]
        match = re.match(
            "(?i)Week of (?P<month>.*) (?P<day>\d+), (?P<year>\d{4})",
            week_of)
        day_info = match.groupdict()
        monday_dom = int(day_info['day'])
        days = ["monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday"]

        dates = {}
        dIdex = 0
        for row in header.xpath(".//td")[1:]:
            date = row.text_content()
            date = re.sub("\s+", " ", date).strip()
            dates[dIdex] = date
            dIdex += 1

        def _parse_time_block(block):
            if block.strip() == "No Meeting":
                return None, None, []
            bills = []
            room = None

            blocks = [ x.strip() for x in block.split("\n") ]

            hour = re.sub("\(.*\)", "", blocks[1])
            bills = blocks[2]
            bills = bills.encode('ascii', errors='ignore')

            if "after" in hour or "after" in bills:
                return None, None, []

            # Extra time cleanup
            # "Rm"
            if "Rm" in hour:
                inf = hour.split("Rm")
                assert len(inf) == 2
                room = inf[1]
                hour = inf[0]

            # "and"
            hour = [ x.strip() for x in hour.split('and') ]

            # We'll pass over this twice.
            single_bill = re.search("(H|S)(C?)(B|R) \d+", bills)
            if single_bill is not None:
                start, end = single_bill.regs[0]
                description = bills
                bills = bills[start:end]
                bills = [{
                    "bill_id": bills,
                    "description": description
                }]
            else:
                multi_bills = re.search("(H|S)(B|R|M)s (\d+((;,) )?)+",
                                        bills)
                if multi_bills is not None:
                    # parse away.
                    bill_array = bills.split()
                    type = bill_array[0]
                    bill_array = bill_array[1:]

                    def _c(f):
                        for thing in [";", ",", "&", "*"]:
                            f = f.replace(thing, "")
                        return re.sub("\s+", " ", f).strip()

                    bill_array = [_c(x) for x in bill_array]
                    type = type.replace("s", "")
                    bill_array = [
                        { "bill_id": "%s %s" % ( type, x ),
                          "description": bills } for x in bill_array ]
                    bills = bill_array

                else:
                    self.warning("Unknwon bill thing: %s" % (bills))
                    bills = []

            return hour, room, bills

        for row in rows:
            tds = row.xpath(".//td")
            ctty = re.sub("\s+", " ", tds[0].text_content().strip())
            times = tds[1:]
            for i in range(0, len(times)):
                hours, room, bills = _parse_time_block(times[i].text_content())
                if hours is None or bills == []:
                    continue

                for hour in hours:
                    datetime = "%s %s" % ( dates[i], hour )
                    datetime = datetime.encode("ascii", "ignore")

                    # DAY_OF_WEEK MONTH/DAY/YY %I:%M %p"
                    dow, time = datetime.split()
                    month = day_info['month']
                    year = day_info['year']
                    day = monday_dom + days.index(dow.lower())

                    datetime = "%s %s %s, %s %s" % (
                        dow, month, day, year, time
                    )

                    formats = [
                        "%A %B %d, %Y %I:%M %p",
                        "%A %B %d, %Y %I:%M%p",
                        "%A %B %d, %Y %I %p",
                        "%A %B %d, %Y %I%p",
                    ]

                    dtobj = None
                    for fmt in formats:
                        try:
                            dtobj = dt.datetime.strptime(datetime, fmt)
                        except ValueError as e:
                            continue

                    if dtobj is None:
                        self.warning("Unknown guy: %s" % (datetime))
                        raise Exception

                    datetime = dtobj

                    event = Event(session,
                                  datetime,
                                  'committee:meeting',
                                  'Meeting Notice',
                                  "Room %s" % (room))
                    event.add_source(url)

                    for bill in bills:
                        event.add_related_bill(
                            bill['bill_id'],
                            description=bill['description'],
                            type='consideration'
                        )

                    event.add_participant("host",
                                          ctty, 'committee', chamber=chamber)
                    self.save_event(event)

    def scrape(self, chamber, session):
        if chamber != "lower":
            self.warning("Sorry, we can't scrape !(lower) ATM. Skipping.")
            return

        self.scrape_page(chamber, session)
