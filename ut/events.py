import re
import datetime

from openstates.utils import LXMLMixin
from billy.scrape.events import EventScraper, Event
from scrapelib import HTTPError


class UTEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'ut'

    def scrape(self, session, chambers):
        URL = 'http://utahlegislature.granicus.com/ViewPublisherRSS.php?view_id=2&mode=agendas'
        doc = self.lxmlize(URL)
        events = doc.xpath('//item')

        for info in events:
            title_and_date = info.xpath('title/text()')[0].split(" - ")
            title = title_and_date[0]
            when = title_and_date[-1]
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
            try:
                doc = self.lxmlize(url)
            except HTTPError:
                self.logger.warning("Page missing, skipping")
                continue
            event.add_source(url)

            committee = doc.xpath('//a[text()="View committee page"]/@href')
            if committee:
                committee_doc = self.lxmlize(committee[0])
                committee_name = committee_doc.xpath(
                        '//h3[@class="heading committee"]/text()')[0].strip()
                if committee_name.lower().startswith("Senate"):
                    chamber = "upper"
                elif committee_name.lower().startswith("House"):
                    chamber = "lower"
                else:
                    chamber = "joint"
                event.add_participant(
                        type='host',
                        participant=committee_name,
                        participant_type='committee',
                        chamber = chamber
                        )

            documents = doc.xpath('.//td')
            for document in documents:
                url = re.search(r'(http://.*?pdf)', document.xpath('@onclick')[0])
                if url is None:
                    continue
                url = url.group(1)
                event.add_document(
                        name=document.xpath('text()')[0],
                        url=url,
                        mimetype='application/pdf'
                        )
                bills = document.xpath('@onclick')
                for bill in bills:
                    if "bills/static" in bill:
                        bill_name = bill.split("/")[-1].split(".")[0]
                        event.add_related_bill(bill_name,
                            type='consideration',
                            description='Bill up for discussion')



            self.save_event(event)
