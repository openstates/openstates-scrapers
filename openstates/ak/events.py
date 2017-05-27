import pytz
import datetime

from openstates.utils import LXMLMixin
from pupa.scrape import Scraper, Event


class AKEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone('US/Alaska')
    _DATETIME_FORMAT = '%m/%d/%Y %I:%M %p'

    def scrape(self):
        EVENTS_URL = 'http://www.akleg.gov/basis/Meeting/Find'
        events = self.lxmlize(EVENTS_URL).xpath('//ul[@id="meetingResults"]/li')
        for info in events:
            event_url = info.xpath('span[@class="col04"]/a/@href')[0]
            doc = self.lxmlize(event_url)

            # Skip events that are placeholders or tentative
            # Also skip whole-chamber events
            if any(x.strip().startswith("No Meeting") for x in
                    doc.xpath('//div[@class="schedule"]//text()')) \
                    or "session" in \
                    info.xpath('span[@class="col01"]/text()')[0].lower():
                continue

            name = " ".join(
                x.strip()
                for x in doc.xpath('//div[@class="schedule"]//text()')
                if x.strip()
            )

            # Skip events with no name
            if not name:
                continue

            event = Event(
                start_time=self._TZ.localize(
                    datetime.datetime.strptime(
                        info.xpath('span[@class="col02"]/text()')[0],
                        self._DATETIME_FORMAT,
                    )
                ),
                timezone=self._TZ.zone,
                name=name,
                location_name=doc.xpath(
                    '//div[@class="heading-container"]/span/text()'
                )[0].title()
            )

            event.add_participant(
                info.xpath('span[@class="col01"]/text()')[0].title(),
                type='committee',
                note='host',
            )

            for document in doc.xpath('//td[@data-label="Document"]/a'):
                event.add_document(
                    document.xpath('text()')[0],
                    url=document.xpath('@href')[0]
                )

            event.add_source(EVENTS_URL)
            event.add_source(event_url.replace(" ", "%20"))

            yield event
