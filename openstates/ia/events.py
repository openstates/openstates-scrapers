import re
import datetime

from billy.scrape.events import EventScraper, Event

import lxml.html


class IAEventScraper(EventScraper):
    state = 'ia'

    def scrape(self, chamber, session):
        if chamber == 'other':
            return

        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=10)
        end_date = today + datetime.timedelta(days=10)

        if chamber == 'upper':
            chamber_abbrev = 'S'
        else:
            chamber_abbrev = 'H'

        url = ("http://www.legis.iowa.gov/Schedules/meetingsList"
               "Chamber.aspx?chamber=%s&bDate=%02d/%02d/"
               "%d&eDate=%02d/%02d/%d" % (chamber_abbrev,
                                          start_date.month,
                                          start_date.day,
                                          start_date.year,
                                          end_date.month,
                                          end_date.day,
                                          end_date.year))

        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)
        for link in page.xpath("//a[contains(@id, 'linkCommittee')]"):
            comm = link.text.strip()
            desc = comm + " Committee Hearing"
            location = link.xpath("string(../../td[3])")

            when = link.xpath("string(../../td[1])").strip()
            if when == 'Cancelled':
                continue

            if 'AM' in when:
                when = when.split('AM')[0] + " AM"
            else:
                when = when.split('PM')[0] + " PM"

            when = datetime.datetime.strptime(when, "%m/%d/%Y %I:%M %p")

            event = Event(session, when, 'committee:meeting',
                          desc, location)
            event.add_source(url)
            self.save_event(event)
