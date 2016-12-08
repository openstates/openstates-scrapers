from datetime import datetime as datetime
import re

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper
from openstates.utils import LXMLMixin

import lxml.html
import pytz

url = "http://www.leg.state.mn.us/calendarday.aspx?jday=all"

class MNEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'mn'
    date_formats = (
        '%A, %B %d, %Y %I:%M %p',
        '%A, %B %d'
    )

    def scrape(self, chamber, session):
        self.session = session

        page = self.lxmlize(url)

        commission_meetings = page.xpath("//div[@class='Comm_item']")
        self.scrape_meetings(commission_meetings, 'commission')

        house_meetings = page.xpath("//div[@class='house_item']")
        self.scrape_meetings(house_meetings, 'house')

        senate_meetings = page.xpath("//div[@class='senate_item']")
        self.scrape_meetings(senate_meetings, 'senate')

    def scrape_meetings(self, meetings, group):
        """
        Scrape and save event data from a list of meetings.

        Arguments:
        meetings -- A list of lxml elements containing event information
        group -- The type of meeting. The legislature site applies
                 different formatting to events based on which group
                 they correspond to.  `group` should be one of the
                 following strings: 'house', 'senate', or 'commission'.

        """
        for meeting in meetings:
            when = self.get_date(meeting)
            description = self.get_description(meeting)
            location = self.get_location(meeting)

            if when and description and location:
                kwargs = {}
                if group in self.metadata['chambers'].keys():
                    kwargs['chamber'] = group
                agenda = self.get_agenda(meeting)
                if agenda:
                    kwargs['agenda'] = agenda

                # Event prototype is as follows:
                # class Event(SourcedObject):
                #    def __init__(self, session, when, type,
                #                 description, location, end=None, **kwargs)
                event = Event(self.session, when, 'committee:meeting',
                        description, location, **kwargs)
                event.add_source(url)
                self.save_event(event)

    def get_date(self, meeting):
        """
        Get the date from a meeting lxml element.

        Arguments:
        meeting -- A lxml element containing event information

        """
        date_raw = meeting.xpath(".//b")
        if len(date_raw) < 1:
            return

        date_string = date_raw[0].text_content().strip()

        for date_format in self.date_formats:
            try:
                date = datetime.strptime(date_string, date_format)
                return date
            except ValueError:
                pass

    def get_description(self, meeting, i=0):
        """
        Get the description from a meeting lxml element.

        Because some events include a "House" or "Senate" `span`
        before the `span` containing the description, a repetitive
        search is necessary.

        TODO Other events include a date span before the span
        containing the description.

        Arguments:
        meeting -- A lxml element containing event information
        i -- The index of `a`/`span` tags to look for.

        """
        description_raw = meeting.xpath(".//a")
        if (len(description_raw) < 1 or
                description_raw[0].text_content() == ''):
            description_raw = meeting.xpath(".//span")
        if len(description_raw) < (i + 1):
            return

        description = description_raw[i].text_content().strip()

        if description == 'House' or description == 'Senate':
            return self.get_description(meeting, i + 1)

        return description

    def get_location(self, meeting):
        """
        Get the location from a meeting lxml element.

        Location information follows a `b` element containing the text
        "Room:".

        Arguments:
        meeting -- A lxml element containing event information

        """
        return self.get_tail_of(meeting, '^Room:')

    def get_agenda(self, meeting):
        """
        Get the agenda from a meeting lxml element.

        Agenda information follows a `b` element containing the text
        "Agenda:".

        Arguments:
        meeting -- A lxml element containing event information

        """
        return self.get_tail_of(meeting, '^Agenda:')

    def get_tail_of(self, meeting, pattern_string):
        """
        Get the tail of a `b` element matching `pattern_string`, all
        inside a `p` tag.

        Surprisingly useful for the markup on the Minnesota
        legislative events calendar page.

        Arguments:
        pattern_string -- A regular expression string to match
                          against

        """
        pattern = re.compile(pattern_string)

        p_tags = meeting.xpath(".//p")
        if len(p_tags) < 1:
            return

        p_tag = p_tags[0]

        for element in p_tag.iter():
            if element.tag == 'b':
                raw = element.text_content().strip()
                r = pattern.search(raw)
                if r and element.tail:
                    tail = element.tail.strip()
                    if tail != '':
                        return tail
                    break
        return

