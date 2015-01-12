import re
import requests
import datetime as dt
import scrapelib

from openstates.utils import LXMLMixin
from billy.scrape.events import EventScraper, Event

import pytz
import lxml.etree
import lxml.html

url = 'http://utahlegislature.granicus.com/ViewPublisherRSS.php?view_id=2&mode=agendas'

class UTEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'ut'
    _tz = pytz.timezone('US/Mountain')

    def scrape_page(self, url, session, chamber):
        try:
            try:
                page = self.lxmlize(url)
            except requests.exceptions.Timeout:
                self.warning("Erm, we got a timeout here. Bailing")
                return

        except lxml.etree.XMLSyntaxError:
            self.warning("Ugh. Invalid HTML")
            return  # Ugh, invalid HTML.
        agendas = page.xpath("//td[@class='numberspace']")

        spans = page.xpath("//center/span")
        ctty = None
        date = None
        time = None
        if len(spans) >= 4:
            ctty = spans[0].text_content().strip()
            date = spans[2].text_content().strip()
            time = spans[3].text_content().strip()

        bills = []
        for agenda in agendas:
            number = agenda.text_content()
            string = agenda.getnext().text_content().strip()
            re_bills = re.findall("(S|H)\.?(B|R|M)\. (\d+)", string)
            for bill in re_bills:
                bill_id = '%s%s %s' % bill
                bills.append({
                    'name': bill_id,
                    'desc': string
                })

        if ctty is None or date is None or time is None:
            return

        datetime = "%s %s" % (
            date.strip(),
            time.strip()
        )
        datetime = re.sub("AGENDA", "", datetime).strip()
        datetime = [ x.strip() for x in datetime.split("\r\n") ]

        if "" in datetime:
            datetime.remove("")

        if len(datetime) == 1:
            datetime.append("state house")

        where = datetime[1]
        translate = {
            "a.m.": "AM",
            "p.m.": "PM"
        }
        for t in translate:
            datetime[0] = datetime[0].replace(t, translate[t])
        datetime = dt.datetime.strptime(datetime[0], "%A, %B %d, %Y %I:%M %p")

        chamber = 'other'
        cLow = ctty.lower()
        if "seante" in cLow:
            chamber = 'upper'
        elif "house" in cLow:
            chamber = 'lower'
        elif "joint" in cLow:
            chamber = 'joint'

        event = Event(session, datetime, 'committee:meeting',
                      ctty, location=where)
        event.add_source(url)
        event.add_participant('host', ctty, 'committee', chamber=chamber)
        for bill in bills:
            event.add_related_bill(bill['name'],
                                   description=bill['desc'],
                                   type='consideration')
        self.save_event(event)

    def scrape(self, chamber, session):
        if chamber != 'other':
            return

        page = self.urlopen(url)
        page = lxml.etree.fromstring(page)

        for p in page.xpath("//link"):
            try:
                self.scrape_page(p.text, session, chamber)
            except scrapelib.HTTPError:
                continue
