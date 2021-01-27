import re
import datetime
import dateutil.parser
import pytz
from utils import LXMLMixin
from openstates.scrape import Scraper, Event
from scrapelib import HTTPError


class UTEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("MST7MDT")
    base_url = 'https://le.utah.gov'

    def scrape(self, chamber=None):
        url = 'https://le.utah.gov/CalServ/CalServ?month={}&year={}'

        year = datetime.datetime.today().year

        for i in range(0,12):
            page = self.get(url.format(i, year)).json()
            if 'days' in page:
                for day_row in page['days']:
                    for row in day_row['events']:
                        # ignore 'note', 'housefloor', 'senatefloor'
                        if row['type'] == 'meeting':
                            status = 'tentative'
                            title = row['desc']
                            where = row['location']

                            when = dateutil.parser.parse(
                                f"{day_row['year']}-{str(int(day_row['month'])+1)}-{day_row['day']} {row['time']}"
                            )

                            when = self._tz.localize(when)

                            if row['status'] == 'C':
                                status = 'cancelled'

                            print(title, when, where, status)
                            event = Event(
                                name=title,
                                location_name=where,
                                start_date=when,
                                classification="committee-meeting",
                                status=status
                            )


                            if 'agenda' in row:
                                event.add_document('Agenda', f"{self.base_url}{row['agenda']}", media_type="text/html")

                            if 'minutes' in row:
                                event.add_document('Minutes', f"{self.base_url}{row['minutes']}", media_type="text/html")
                      
                            if 'mediaurl' in row:
                                event.add_media_link("Media",  f"{self.base_url}{row['mediaurl']}", media_type="text/html")
                                print(row['mediaurl'])
                                if re.findall(r'mtgID=(\d+)', row['mediaurl']):
                                    hearing_id = re.findall(r'mtgID=(\d+)', row['mediaurl'])[0]
                                    print(hearing_id)
                                    docs_url = f"https://glen.le.utah.gov/committees/meeting/{hearing_id}/1234"
                                    docs_page = self.get(docs_url).json()
                                    if 'meetingMaterials' in docs_page:
                                        for mat in docs_page['meetingMaterials']:
                                            agenda = event.add_agenda_item(mat['description'])
                                            event.add_document(mat['description'], f"{self.base_url}{mat['docUrl']}", media_type="application/pdf")
                                            print(mat)

                            source_url = f"{self.base_url}{row['itemurl']}"
                            event.add_source(source_url)
                            print(source_url)

                            yield event