import re
import datetime

from openstates.utils import LXMLMixin
from billy.scrape.events import EventScraper, Event


class UTEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'ut'

    def scrape(self, session, chambers):
        URL = 'http://utahlegislature.granicus.com/ViewPublisherRSS.php?view_id=2&mode=agendas'
        doc = self.lxmlize(URL)
        events = doc.xpath('//item')

        for info in events:
            (title, when) = info.xpath('title/text()')[0].split(" - ")
            if not when.endswith(session[ :len("20XX")]):
                continue

            event = Event(
                    session=session,
                    when=datetime.datetime.strptime(when, '%b %d, %Y'),
                    type='committee:meeting',
                    description=title,
                    location='State Capitol'
                    )
            event.add_source(URL)

            url = re.search(r'(http://.*?)\s', info.text_content()).group(1)
            doc = self.lxmlize(url)
            event.add_source(url)

            committee = doc.xpath('//a[text()="View committee page"]/@href')
            if committee:
                committee_doc = self.lxmlize(committee[0])
                committee_name = committee_doc.xpath(
                        '//h3[@class="heading committee"]/text()')[0].strip()
                event.add_participant(
                        type='host',
                        participant=committee_name,
                        participant_type='committee'
                        )

            documents = doc.xpath('.//td')
            for document in documents:
                event.add_document(
                        name=document.xpath('text()')[0],
                        url=re.search(r'(http://.*?pdf)', document.xpath('@onclick')[0]).group(1),
                        mimetype='application/pdf'
                        )

            self.save_event(event)
