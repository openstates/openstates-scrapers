import os
import re
import datetime

from billy.scrape.events import EventScraper, Event

import pytz
import lxml.etree


class WAEventScraper(EventScraper):
    state = 'wa'

    _tz = pytz.timezone('US/Pacific')
    _ns = {'wa': "http://WSLWebServices.leg.wa.gov/"}

    def scrape(self, chamber, session):
        url = ("http://wslwebservices.leg.wa.gov/CommitteeMeetingService"
               ".asmx/GetCommitteeMeetings?beginDate=2011-01-10T00:00:00"
               "&endDate=2012-01-10T00:00:00")

        expected_agency = {'upper': 'Senate', 'lower': 'House'}[chamber]

        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page)

            for meeting in page.xpath(
                "//wa:CommitteeMeeting", namespaces=self._ns):

                cancelled = meeting.xpath(
                    "string(wa:Cancelled)", namespaces=self._ns).strip()
                if cancelled.lower() == "true":
                    continue

                agency = meeting.xpath(
                    "string(wa:Agency)",
                    namespaces=self._ns).strip()

                if agency != expected_agency:
                    continue

                dt = meeting.xpath("string(wa:Date)", namespaces=self._ns)
                dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")

                room = meeting.xpath("string(wa:Room)", namespaces=self._ns)
                building = meeting.xpath(
                    "string(wa:Building)", namespaces=self._ns)
                location = "%s, %s" % (room, building)

                comm = meeting.xpath(
                    "string(wa:Committees/wa:Committee[1]/wa:Name)",
                    namespaces=self._ns)

                desc = "Committee Meeting\n%s" % comm

                guid = meeting.xpath(
                    "string(wa:AgendaId)", namespaces=self._ns)

                event = Event(session, dt, 'committee:meeting',
                              desc, location=location, _guid=guid)

                for comm_part in meeting.xpath(
                    "wa:Committees/wa:Committee", namespaces=self._ns):
                    name = comm_part.xpath("string(wa:Name)",
                                           namespaces=self._ns)
                    agency = comm_part.xpath("string(wa:Agency)",
                                             namespaces=self._ns)
                    name = "%s %s Committee" % (agency, name)

                    event.add_participant('committee', name)

                self.save_event(event)
