from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape
from dateutil import parser, relativedelta
import datetime
import lxml
import pytz


class MTEventScraper(Scraper):
    _tz = pytz.timezone("America/Denver")
    base_url = "http://laws.leg.mt.gov/"

    # the state lists out by bill, we want to cluster by event
    events = {}

    def scrape(self, session=None, start=None, end=None):
        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                session_slug = i["_scraped_name"]

        url = (
            "http://laws.leg.mt.gov/legprd/LAW0240W$CMTE.ActionQuery?P_SESS={session_slug}"
            "&P_COM_NM=&P_ACTN_DTM={start}&U_ACTN_DTM={end}&Z_ACTION2=Find"
        )

        if start is None:
            start = datetime.datetime.today()
        else:
            start = parser.parse(start)

        if end is None:
            end = start + relativedelta.relativedelta(months=+2)
        else:
            end = parser.parse(end)

        url = url.format(
            session_slug=session_slug,
            start=start.strftime("%m/01/%Y"),
            end=end.strftime("%m/%d/%Y"),
        )

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        if len(page.xpath("//p[contains(text(), 'No Records')]")) == 2:
            raise EmptyScrape
        page.make_links_absolute(url)

        for row in page.xpath("//table[@border]/tr"):
            # skip table headers
            if not row.xpath("td[1]/a"):
                continue
            com = row.xpath("td[1]/a[1]/text()")[0].strip()
            com = com.replace("(H)", "House").replace("(S)", "Senate")
            day = row.xpath("td[2]/text()")[0].strip()
            try:
                time = row.xpath("td[3]/text()")[0].strip()
            except Exception:
                time = None
            room = row.xpath("td[4]")[0].text_content().strip()
            if not room:
                room = "See Agenda"
            bill = row.xpath("td[5]/a[1]/text()")[0].strip()
            bill_title = row.xpath("td[6]/text()")[0].strip()

            if time:
                when = parser.parse(f"{day} {time}")
            else:
                when = parser.parse(day)
            when = self._tz.localize(when)

            when_slug = when.strftime("%Y%m%d%H%I")
            if com not in self.events:
                self.events[com] = {}

            if when_slug not in self.events[com]:
                event = Event(
                    name=com,
                    location_name=room,
                    start_date=when,
                    classification="committee-meeting",
                )
                event.add_source(row.xpath("td[1]/a[1]/@href")[0])
            else:
                event = self.events[com][when_slug]

            event.add_committee(com)

            agenda = event.add_agenda_item(bill_title)
            agenda.add_bill(bill)

            if row.xpath('.//a[contains(@href,"/billhtml/")]'):
                bill_url = row.xpath('.//a[contains(@href,"/billhtml/")]/@href')[0]
                event.add_document(
                    bill_title, bill_url, media_type="text/html", on_duplicate="ignore"
                )
            if row.xpath('.//a[contains(@href,"/billpdf/")]'):
                bill_url = row.xpath('.//a[contains(@href,"/billpdf/")]/@href')[0]
                event.add_document(
                    bill_title,
                    bill_url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

            # both media links are incorrectly labelled "audio", but the first
            # seems to always be video, and if there's only one it's video
            media_links = row.xpath('.//a[contains(@href, "sliq.net")]/@href')
            if len(media_links) > 0:
                event.add_media_link(
                    "Video",
                    media_links[0],
                    media_type="text/html",
                    on_duplicate="ignore",
                )
            if len(media_links) == 2:
                event.add_media_link(
                    "Audio",
                    media_links[1],
                    media_type="text/html",
                    on_duplicate="ignore",
                )

            self.events[com][when_slug] = event

        for com in self.events:
            for date in self.events[com]:
                yield self.events[com][date]
