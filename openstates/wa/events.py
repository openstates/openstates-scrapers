from openstates.utils import LXMLMixin
from datetime import timedelta
import datetime

import pytz
import lxml

from pupa.scrape import Scraper, Event
from .utils import xpath


class WAEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Pacific")
    _ns = {"wa": "http://WSLWebServices.leg.wa.gov/"}

    meetings = None

    chambers = {"Senate": "upper", "House": "lower", "Agency": "joint"}

    def scrape(self, chamber=None, session=None, start=None, end=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        now = datetime.datetime.now()
        print_format = "%Y-%m-%d"

        if start is None:
            start = now.strftime(print_format)
        else:
            start = datetime.datetime.strptime(start, "%Y-%m-%d").strftime(print_format)

        if end is None:
            end = (now + timedelta(days=30)).strftime(print_format)
        else:
            end = datetime.datetime.strptime(end, "%Y-%m-%d").strftime(print_format)

        chambers = [chamber] if chamber else ["upper", "lower", "joint"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session, start, end)

    # Only need to fetch the XML once for both chambers
    def get_xml(self, start, end):
        if self.meetings is not None:
            return self.meetings

        event_url = (
            "http://wslwebservices.leg.wa.gov/CommitteeMeetingService.asmx"
            "/GetCommitteeMeetings?beginDate={}&endDate={}"
        )

        url = event_url.format(start, end)

        page = self.get(url).content
        page = lxml.etree.fromstring(page)

        self.meetings = page
        return page

    def scrape_chamber(self, chamber, session, start, end):
        page = self.get_xml(start, end)

        for row in xpath(page, "//wa:CommitteeMeeting"):
            event_cancelled = xpath(row, "string(wa:Cancelled)")
            if event_cancelled == "true":
                continue

            event_chamber = xpath(row, "string(wa:Agency)")
            if self.chambers[event_chamber] != chamber:
                continue

            event_date = datetime.datetime.strptime(
                xpath(row, "string(wa:Date)"), "%Y-%m-%dT%H:%M:%S"
            )
            event_date = self._tz.localize(event_date)
            event_com = xpath(row, "string(wa:Committees/" "wa:Committee/wa:LongName)")
            agenda_id = xpath(row, "string(wa:AgendaId)")
            notes = xpath(row, "string(wa:Notes)")
            room = xpath(row, "string(wa:Room)")
            building = xpath(row, "string(wa:Building)")
            # XML has a wa:Address but it seems useless
            city = xpath(row, "string(wa:City)")
            state = xpath(row, "string(wa:State)")

            location = "{}, {}, {} {}".format(room, building, city, state)

            event = Event(
                name=event_com,
                start_date=event_date,
                location_name=location,
                description=notes,
            )

            source_url = "https://app.leg.wa.gov/committeeschedules/Home/Agenda/{}".format(
                agenda_id
            )
            event.add_source(source_url)

            event.add_participant(event_com, type="committee", note="host")

            event.extras["agendaId"] = agenda_id

            self.scrape_agenda_items(agenda_id, event)

            yield event

    def scrape_agenda_items(self, agenda_id, event):
        agenda_url = (
            "http://wslwebservices.leg.wa.gov/CommitteeMeetingService.asmx/"
            "GetCommitteeMeetingItems?agendaId={}".format(agenda_id)
        )

        page = self.get(agenda_url).content
        page = lxml.etree.fromstring(page)

        rows = xpath(page, "//wa:CommitteeMeetingItem")

        for row in rows:
            bill_id = xpath(row, "string(wa:BillId)")
            desc = xpath(row, "string(wa:ItemDescription)")

            if bill_id:
                item = event.add_agenda_item(desc)
                item.add_bill(bill_id)
