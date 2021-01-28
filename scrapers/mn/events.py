from datetime import datetime
import re
import pprint
import dateutil.parser
import pytz
from openstates.scrape import Scraper
from openstates.scrape import Event

from utils import LXMLMixin

url = "http://www.leg.state.mn.us/calendarday.aspx?jday=all"


class MNEventScraper(Scraper, LXMLMixin):
    # bad SSL as of August 2017
    verify = False
    _tz = pytz.timezone("US/Central")

    def scrape(self):
        # https://www.senate.mn/api/schedule/upcoming
        # https://www.house.leg.state.mn.us/Schedules/All

        yield from self.scrape_upper()

    def scrape_upper(self):
        url = 'https://www.senate.mn/api/schedule/upcoming'
        data = self.get(url).json()

        for row in data['events']:
            pprint.pprint(row)

            com = row['committee']['committee_name']
            start = dateutil.parser.parse(row['hearing_start'])
            start = self._tz.localize(start)

            if row['hearing_room'] and 'hearing_building' in row and row['hearing_building']:
                where = f"{row['hearing_building']} {row['hearing_room']}"
            elif 'hearing_building' in row and row['hearing_building']:
                where = row['hearing_building']
            else:
                where = 'TBD'

            description = ''

            if 'hearing_notes' in row and row['hearing_notes']:
                description = row['hearing_notes']

            event = Event(
                name=com,
                location_name=where,
                start_date=start,
                classification="committee-meeting",
                description=description
            )

            if 'lrl_schedule_link' in row:
                event.add_source(row['lrl_schedule_link'])
            else:
                if row['committee']['link'].startswith('http'):
                    event.add_source(row['committee']['link'])
                elif  row['committee']['link'].startswith('www'):
                    event.add_source(f"http://{row['committee']['link']}")
                else:
                    event.add_source(f"https://www.senate.mn/{row['committee']['link']}")

            if 'agenda' in row:
                for agenda_row in row['agenda']:
                    agenda = event.add_agenda_item(agenda_row['description'])
                    if 'bill_type' in agenda_row:
                        agenda.add_bill("{} {}".format(agenda_row['bill_type'].replace('.',''), agenda_row['bill_number']))

                    if 'files' in agenda_row:
                        for file_row in agenda_row['files']:
                            event.add_document(file_row['filename'], f"https://www.senate.mn/{file_row['file_path']}", media_type="text/html")

            if 'video_link' in row:
                event.add_media_link('Video', row['video_link'], 'text/html')

            if 'audio_link' in row:
                event.add_media_link('Audio', row['audio_link'], 'text/html')

            yield event