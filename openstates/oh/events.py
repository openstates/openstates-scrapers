import re
import datetime as dt

from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html

pages = {
    "lower" : "http://www.legislature.state.oh.us/house_committee_schedule.cfm"
}

class OHEventScraper(EventScraper):
    jurisdiction = 'oh'

    _tz = pytz.timezone('US/Eastern')

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape_page(self, chamber, session):
        url = pages[chamber]
        page = self.lxmlize(url)

        rows = page.xpath("//table[@class='MsoNormalTable']/tr")
        header = rows[0]
        rows = rows[1:]

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
            single_bill = re.search("(H|S)(B|R) \d{3}", bills)
            if single_bill is not None:
                start, end = single_bill.regs[0]
                description = bills
                bills = bills[start:end]
                bills = [{
                    "bill_id": bills,
                    "description": description
                }]
            else:
                multi_bills = re.search("(H|S)(B|R|M)s (\d{3}(; )?)+", bills)
                if multi_bills is not None:
                    # parse away.
                    bill_array = bills.split()
                    type = bill_array[0]
                    bill_array = bill_array[1:]
                    bill_array = [ x.replace(";", "").strip() for
                                   x in bill_array ]
                    type = type.replace("s", "")
                    bill_array = [
                        { "bill_id": "%s %s" % ( type, x ),
                          "description": bills } for x in bill_array ]
                    bills = bill_array

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
                    datetime = dt.datetime.strptime(datetime,
                                                    "%A %m/%d/%y %I:%M %p")
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
                    event.add_participant("host", ctty, 'committee', chamber=chamber)
                    self.save_event(event)

    def scrape(self, chamber, session):
        if chamber != "lower":
            self.warning("Sorry, we can't scrape !(lower) ATM. Skipping.")
            return

        self.scrape_page(chamber, session)
