import datetime
import os
import re

import pytz

from billy.scrape.events import EventScraper, Event
from billy.scrape.utils import convert_pdf


class OHEventScraper(EventScraper):
    jurisdiction = 'oh'
    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        if chamber == "lower":
            self.scrape_lower(session)
        elif chamber == 'upper':
            self.scrape_upper(session)

    def scrape_lower(self, session):
        PDF_URL = 'http://www.ohiohouse.gov/Assets/CommitteeSchedule/calendar.pdf'
        (path, _response) = self.urlretrieve(PDF_URL)
        text = convert_pdf(path, type='text')
        os.remove(path)

        days = re.split(r'(\w+day, \w+ \d{1,2}, 20\d{2})', text)
        date = None
        for day in enumerate(days[1: ]):
            if day[0] % 2 == 0:
                date = day[1]
            else:

                events = re.split(r'\n((?:\w+\s?)+)\n', day[1])
                comm = ''
                for event in enumerate(events[1: ]):
                    if event[0] % 2 == 0:
                        comm = event[1].strip()
                    else:

                        try:
                            (time, location, description) = re.search(
                                    r'''(?mxs)
                                    (\d{1,2}:\d{2}\s[ap]\.m\.)  # Meeting time
                                    .*?,\s  # Potential extra text for meeting time
                                    (.*?),\s  # Location, usually a room
                                    .*?\n  # Chairman of committee holding event
                                    (.*)  # Description of event
                                    ''',
                                    event[1]).groups()
                        except AttributeError:
                            continue

                        time = time.replace(".", "").upper()
                        time = datetime.datetime.strptime(
                                time + "_" + date,
                                '%I:%M %p_%A, %B %d, %Y'
                                )
                        time = self._tz.localize(time)

                        location = location.strip()

                        description = '\n'.join([
                                x.strip() for x in
                                description.split('\n')
                                if x.strip() and not x.strip()[0].isdigit()
                                ]).decode('ascii', 'ignore')

                        if not description:
                            description = '[No description provided by state]'

                        event = Event(
                                session=session,
                                when=time,
                                type='committee:meeting',
                                description=description,
                                location=location
                                )

                        event.add_source(PDF_URL)
                        event.add_participant(
                                type='host',
                                participant=comm,
                                participant_type='committee',
                                chamber='lower'
                                )
                        for line in description.split('\n'):
                            related_bill = re.search(r'(H\.?(?:[JC]\.?)?[BR]\.?\s+\d+)\s+(.*)$', line)
                            if related_bill:
                                (related_bill, relation) = related_bill.groups()
                                relation = relation.strip()
                                related_bill = related_bill.replace(".", "")
                                event.add_related_bill(
                                        bill_id=related_bill,
                                        type='consideration',
                                        description=relation
                                        )

                        self.save_event(event)

    def scrape_upper(self, session):
        PDF_URL = 'http://www.ohiosenate.gov/Assets/CommitteeSchedule/calendar.pdf'
        (path, _response) = self.urlretrieve(PDF_URL)
        text = convert_pdf(path, type='text')
        os.remove(path)

        days = re.split(r'(\w+day, \w+ \d{1,2})', text)
        date = None
        for day in enumerate(days[1: ]):
            if day[0] % 2 == 0:
                # Calendar is put out for the current week, so use that year
                date = day[1] + ", " + str(datetime.datetime.now().year)
            else:

                events = re.split(r'\n\n((?:\w+\s?)+),\s', day[1])
                comm = ''
                for event in enumerate(events[1: ]):
                    if event[0] % 2 == 0:
                        comm = event[1].strip()
                    else:

                        try:
                            (time, location, description) = re.search(
                                    r'''(?mxs)
                                    (\d{1,2}:\d{2}\s[AP]M)  # Meeting time
                                    .*?,\s  # Potential extra text for meeting time
                                    (.*?)\n  # Location, usually a room
                                    .*?\n  # Chairman of committee holding event
                                    (.*)  # Description of event
                                    ''',
                                    event[1]).groups()
                        except AttributeError:
                            continue

                        time = datetime.datetime.strptime(
                                time + "_" + date,
                                '%I:%M %p_%A, %B %d, %Y'
                                )
                        time = self._tz.localize(time)

                        location = location.strip()

                        description = '\n'.join([
                                x.strip() for x in
                                description.split('\n')
                                if 
                                        x.strip() and
                                        not x.strip().startswith("Page ") and
                                        not x.strip().startswith("*Possible Vote") and
                                        not x.strip() == "NO OTHER COMMITTEES WILL MEET"
                                ]).decode('ascii', 'ignore')

                        if not description:
                            description = '[No description provided by state]'

                        event = Event(
                                session=session,
                                when=time,
                                type='committee:meeting',
                                description=description,
                                location=location
                                )

                        event.add_source(PDF_URL)
                        event.add_participant(
                                type='host',
                                participant=comm,
                                participant_type='committee',
                                chamber='upper'
                                )
                        for line in description.split('\n'):
                            related_bill = re.search(r'(S\.?(?:[JC]\.?)?[BR]\.?\s+\d+)\s+(.*)$', line)
                            if related_bill:
                                (related_bill, relation) = related_bill.groups()
                                relation = relation.strip()
                                related_bill = related_bill.replace(".", "")
                                event.add_related_bill(
                                        bill_id=related_bill,
                                        type='consideration',
                                        description=relation
                                        )

                        self.save_event(event)
