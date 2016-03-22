import datetime as dt

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper
from openstates.utils import LXMLMixin

import lxml.html
import pytz

agenda_url = "http://status.rilin.state.ri.us/agendas.aspx"
column_order = {
    "upper" : 1,
    "other" : 2,
    "lower" : 0
}

all_day = [  # ugh, hack
    "Rise of the House",
    "Rise of the Senate",
    "Rise of the House & Senate"
]
replace = {
    "House Joint Resolution No." : "HJR",
    "House Resolution No." : "HR",
    "House Bill No." : "HB",

    "Senate Joint Resolution No." : "SJR",
    "Senate Resolution No." : "SR",
    "Senate Bill No." : "SB",
    u"\xa0" : " ",
    "SUB A" : "",
    "SUB A as amended": ""
}

class RIEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'ri'

    _tz = pytz.timezone('US/Eastern')

    def scrape_agenda(self, url, session):
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
        date = metainf['DATE:']
        time = metainf['TIME:']
        where = metainf['PLACE:']
        fmts = [
            "%A, %B %d, %Y",
            "%A, %B %d, %Y %I:%M %p",
            "%A, %B %d, %Y %I:%M",
        ]

        kwargs = {}
        if time in all_day:
            datetime = date
        else:
            datetime = "%s %s" % ( date, time )
        if "CANCELLED" in datetime.upper():
            return

        event_desc = "Meeting Notice"
        if "Rise of the" in datetime:
            datetime = date
            kwargs["all_day"] = True
            event_desc = "Meeting Notice: Starting at {}".format(time)


        transtable = {
            "P.M" : "PM",
            "PM." : "PM",
            "P.M." : "PM",
            "A.M." : "AM",
            "POSTPONED" : "",
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

        event = Event(session, datetime, 'committee:meeting',
                      event_desc, location=where, **kwargs)
        event.add_source(url)
        # aight. Let's get us some bills!
        bills = page.xpath("//b/a")
        for bill in bills:
            bill_ft = bill.attrib['href']
            event.add_document(bill.text_content(), bill_ft, type="full-text",
                               mimetype="application/pdf")
            root = bill.xpath('../../*')
            root = [ x.text_content() for x in root ]
            bill_id = "".join(root)

            if "SCHEDULED FOR" in bill_id:
                continue

            descr = bill.getparent().getparent().getparent().getnext().getnext(
                ).text_content()

            for thing in replace:
                bill_id = bill_id.replace(thing, replace[thing])

            event.add_related_bill(bill_id,
                                   description=descr,
                                   type='consideration')
        committee = page.xpath("//span[@id='lblSession']")[0].text_content()
        chambers = {
            "house" : "lower",
            "joint" : "joint",
            "senate" : "upper"
        }
        chamber = "other"
        for key in chambers:
            if key in committee.lower():
                chamber = chambers[key]

        event.add_participant("host", committee, 'committee', chamber=chamber)

        self.save_event(event)

    def scrape_agenda_dir(self, url, session):
        page = self.lxmlize(url)
        rows = page.xpath("//table[@class='agenda_table']/tr")[2:]
        for row in rows:
            url = row.xpath("./td")[-1].xpath(".//a")[0]
            self.scrape_agenda(url.attrib['href'], session)

    def scrape(self, chamber, session):
        offset = column_order[chamber]
        page = self.lxmlize(agenda_url)
        rows = page.xpath("//table[@class='agenda_table']/tr")[1:]
        for row in rows:
            ctty = row.xpath("./td")[offset]
            to_scrape = ctty.xpath("./a")
            for page in to_scrape:
                self.scrape_agenda_dir(page.attrib['href'], session)
