import datetime
import json

from billy.scrape.events import Event, EventScraper


class VTEventScraper(EventScraper):
    jurisdiction = 'vt'

    def scrape(self, session, chambers):
        year_slug = session[5: ]
        url = 'http://legislature.vermont.gov/committee/loadAllMeetings/{}'.\
                format(year_slug)

        json_data = self.get(url).text
        events = json.loads(json_data)['data']
        for info in events:

            # Determine when the committee meets
            if info['TimeSlot'] == '1':
                when = datetime.datetime.strptime(info['MeetingDate'], '%A, %B %d, %Y')
                all_day = True
            else:
                try:
                    when = datetime.datetime.strptime(
                            info['MeetingDate'] + ', ' + info['TimeSlot'],
                            '%A, %B %d, %Y, %I:%M %p'
                            )
                except ValueError:
                    when = datetime.datetime.strptime(
                            info['MeetingDate'] + ', ' + info['StartTime'],
                            '%A, %B %d, %Y, %I:%M %p'
                            )
                all_day = False

            event = Event(
                    session=session,
                    when=when,
                    all_day=all_day,
                    type='committee:meeting',
                    description="Meeting of the {}".format(info['LongName']),
                    location="{0}, Room {1}".format(info['BuildingName'], info['RoomNbr'])
                    )
            event.add_source(url)
            event.add_participant(
                    type='host',
                    participant=info['LongName'],
                    participant_type='committee'
                    )

            self.save_event(event)
