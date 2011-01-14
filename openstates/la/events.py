import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import lxml.html


def parse_datetime(s, year):
    dt = None

    match = re.match(r"[A-Z][a-z]{2,2} \d+, \d\d:\d\d (AM|PM)", s)
    if match:
        dt = datetime.datetime.strptime(match.group(0), "%b %d, %H:%M %p")

    match = re.match(r"[A-Z][a-z]{2,2} \d+", s)
    if match:
        dt = datetime.datetime.strptime(match.group(0), "%b %d").date()

    if dt:
        return dt.replace(year=int(year))
    else:
        raise ValueError("Bad date string: %s" % s)


class LAEventScraper(EventScraper):
    state = 'la'

    def scrape(self, chamber, session):
        if session != '2010':
            raise NoDataForPeriod(session)

        if chamber == 'lower':
            self.scrape_house_weekly_schedule(session)

        self.scrape_committee_schedule(session, chamber)

    def scrape_committee_schedule(self, session, chamber):
        url = "http://www.legis.state.la.us/billdata/bycmte.asp"

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'agenda.asp')]"):
                self.scrape_meeting(self, session, chamber, link.attrib['href'])

    def scrape_meeting(self, session, chamber, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

    def scrape_house_weekly_schedule(self, session):
        url = "http://house.louisiana.gov/H_Sched/Hse_Sched_Weekly.htm"

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//img[@alt = 'See Agenda in pdf']/.."):
                guid = link.attrib['href']

                committee = link.xpath("string(../../../td[1])").strip()

                when_and_where = link.xpath("string(../../../td[2])").strip()

                location = when_and_where.split(',')[-1]
                when = parse_datetime(when_and_where, session)



                description = 'Committee Meeting: %s' % committee

                event = Event(session, when, 'committee:meeting',
                              description, location=location)
                event.add_participant('committee', committee)
                event['link'] = guid

                self.save_event(event)
