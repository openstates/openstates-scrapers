import re
import datetime
import pytz
from scrapers.utils import LXMLMixin
from openstates_core.scrape import Scraper, Event
from scrapelib import HTTPError


class UTEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("MST7MDT")

    def scrape(self, chamber=None):
        URL = "http://utahlegislature.granicus.com/ViewPublisherRSS.php?view_id=2&mode=agendas"
        doc = self.lxmlize(URL)
        events = doc.xpath("//item")

        for info in events:
            title_and_date = info.xpath("title/text()")[0].split(" - ")
            title = title_and_date[0]
            when = title_and_date[-1]
            # if not when.endswith(session[ :len("20XX")]):
            #    continue

            event = Event(
                name=title,
                start_date=self._tz.localize(
                    datetime.datetime.strptime(when, "%b %d, %Y")
                ),
                location_name="State Capitol",
            )
            event.add_source(URL)

            url = re.search(r"(http://.*?)\s", info.text_content()).group(1)
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
                    '//h3[@class="heading committee"]/text()'
                )[0].strip()
                event.add_participant(committee_name, type="committee", note="host")

            documents = doc.xpath(".//td")
            for document in documents:
                url = re.search(r"(http://.*?pdf)", document.xpath("@onclick")[0])
                if url is None:
                    continue
                url = url.group(1)
                event.add_document(
                    note=document.xpath("text()")[0],
                    url=url,
                    media_type="application/pdf",
                )
                bills = document.xpath("@onclick")
                for bill in bills:
                    if "bills/static" in bill:
                        bill_name = bill.split("/")[-1].split(".")[0]
                        item = event.add_agenda_item("Bill up for discussion")
                        item.add_bill(bill_name)
            yield event
