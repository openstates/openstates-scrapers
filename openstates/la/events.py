import re
import pytz
import datetime

from billy.scrape.events import EventScraper, Event
from openstates.utils import LXMLMixin

import lxml.html


def parse_datetime(s, year):
    dt = None

    s = re.sub("\s+", " ", s).strip()

    match = re.match(r"[A-Z][a-z]{2,2} \d+, \d\d:\d\d (AM|PM)", s)
    if match:
        dt = datetime.datetime.strptime(match.group(0), "%b %d, %I:%M %p")

    if dt:
        return dt.replace(year=int(year))

    if dt is None:
        if s.endswith(","):
            s, _ = s.rsplit(" ", 1)
        formats = ["%b %d, %Y, %I:%M %p",
                    "%b %d, %Y %I:%M %p"]

        for f in formats:
            try:
                dt = datetime.datetime.strptime(s, f)
            except ValueError:
                pass
            else:
                return dt

    raise ValueError("Bad date string: %s" % s)


class LAEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'la'
    _tz = pytz.timezone('America/Chicago')

    def scrape(self, session, chambers):
        self.scrape_house_weekly_schedule(session)

        url = "http://www.legis.la.gov/legis/ByCmte.aspx"

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Agenda.aspx')]"):
            self.scrape_meeting(session, link.attrib['href'])

    def scrape_bills(self, line):
        ret = []
        for blob in [x.strip() for x in line.split(",")]:
            if blob == "":
                continue

            if (blob[0] in ['H', 'S', 'J'] and
                    blob[1] in ['R', 'M', 'B', 'C']):
                blob = blob.replace("-", "")
                ret.append(blob)
        return ret

    def scrape_meeting(self, session, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        title ,= page.xpath("//a[@id='linkTitle']//text()")
        date ,= page.xpath("//span[@id='lDate']/text()")
        time ,= page.xpath("//span[@id='lTime']/text()")
        location ,= page.xpath("//span[@id='lLocation']/text()")

        substs = {
            "AM": ["A.M.", "a.m."],
            "PM": ["P.M.", "p.m.", "Noon"],
        }

        for key, values in substs.items():
            for value in values:
                time = time.replace(value, key)

        # Make sure there's a space between the time's minutes and its AM/PM
        if re.search(r'(?i)\d[AP]M$', time):
            time = time[:-2] + " " + time[-2:]

        if "UPON ADJ" in ' '.join(time.split()).upper():
            all_day = True
            when = datetime.datetime.strptime(date, "%B %d, %Y")
        else:
            all_day = False
            when = datetime.datetime.strptime("%s %s" % (
                date, time
            ), "%B %d, %Y %I:%M %p")

        # when = self._tz.localize(when)

        description = "Meeting on %s of the %s" % (date, title)
        chambers = {"house": "lower",
                    "senate": "upper",
                    "joint": "joint",}

        for chamber_, normalized in chambers.items():
            if chamber_ in title.lower():
                chamber = normalized
                break
        else:
            return

        event = Event(
            session,
            when,
            'committee:meeting',
            description,
            location=location,
            all_day=all_day
        )
        event.add_source(url)

        event.add_participant('host', title, 'committee',
                              chamber=chamber)

        trs = iter(page.xpath("//tr[@valign='top']"))
        next(trs)

        for tr in trs:
            try:
                _, _, bill, whom, descr = tr.xpath("./td")
            except ValueError:
                continue

            bill_title = bill.text_content()

            if "S" in bill_title:
                bill_chamber = "upper"
            elif "H" in bill_title:
                bill_chamber = "lower"
            else:
                continue

            event.add_related_bill(bill_id=bill_title,
                                   description=descr.text_content(),
                                   chamber=bill_chamber,
                                   type='consideration')
        self.save_event(event)

    def scrape_house_weekly_schedule(self, session):
        url = "http://house.louisiana.gov/H_Sched/Hse_Sched_Weekly.htm"
        page = self.lxmlize(url)

        for link in page.xpath("//img[@alt = 'See Agenda in pdf']/.."):
            try:
                guid = link.attrib['href']
            except KeyError:
                continue  # Sometimes we have a dead link. This is only on
                # dead entries.

            committee = link.xpath("string(../../td[1])").strip()

            when_and_where = link.xpath("string(../../td[2])").strip()
            when_and_where = re.sub("\s+", " ", when_and_where).strip()
            if "@" in when_and_where:
                continue  # Contains no time data.

            if when_and_where.strip() == "":
                continue

            info = re.match(
                r"(?P<when>.*) (?P<where>L|F|N|H|C.*-.*?)",
                when_and_where
            ).groupdict()

            when_and_where = info['when']
            location = info['where']

            year = datetime.datetime.now().year
            when = parse_datetime(when_and_where, year)  # We can only scrape
            # when = self._tz.localize(when)

            bills = self.scrape_bills(when_and_where)

            description = 'Committee Meeting: %s' % committee

            event = Event(session, when, 'committee:meeting',
                          description, location=location)
            event.add_source(url)
            event.add_participant('host', committee, 'committee',
                                  chamber='lower')
            event.add_document("Agenda", guid, type='agenda',
                               mimetype="application/pdf")
            for bill in bills:
                event.add_related_bill(bill, description=when_and_where,
                                       type='consideration')
            event['link'] = guid

            self.save_event(event)
