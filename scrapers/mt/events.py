from openstates.scrape import Scraper, Event
from dateutil import parser, relativedelta
import datetime
import lxml
import pytz


class MTEventScraper(Scraper):
    _tz = pytz.timezone("America/Denver")
    base_url = "http://laws.leg.mt.gov/"

    # the state lists out by bill, we want to cluster by event
    events = {}

    def scrape(self, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using latest")

        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                session_slug = i["_scraped_name"]

        url = (
            "http://laws.leg.mt.gov/legprd/LAW0240W$CMTE.ActionQuery?P_SESS={session_slug}"
            "&P_COM_NM=&P_ACTN_DTM={start}&U_ACTN_DTM={end}&Z_ACTION2=Find"
        )

        start = datetime.datetime.today()
        # this month and the next 2 months
        end = start + relativedelta.relativedelta(months=+2)

        url = url.format(
            session_slug=session_slug,
            start=start.strftime("%m/01/%Y"),
            end=end.strftime("%m/%d/%Y"),
        )

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath("//table[@border]/tr"):
            # skip table headers
            if not row.xpath("td[1]/a"):
                continue
            day = row.xpath("td[2]/text()")[0].strip()
            time = row.xpath("td[3]/text()")[0].strip()
            room = row.xpath("td[4]")[0].text_content().strip()
            bill = row.xpath("td[5]/a[1]/text()")[0].strip()
            bill_title = row.xpath("td[6]/text()")[0].strip()

            com = row.xpath("td[1]/a[1]/text()")[0].strip()
            com = com.replace("(H)", "House").replace("(S)", "Senate")

            when = parser.parse(f"{day} {time}")
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

            agenda = event.add_agenda_item(bill_title)
            agenda.add_bill(bill)

            if row.xpath('.//a[contains(@href,"/billhtml/")]'):
                bill_url = row.xpath('.//a[contains(@href,"/billhtml/")]/@href')[0]
                event.add_document(bill_title, bill_url, media_type="text/html")
            if row.xpath('.//a[contains(@href,"/billpdf/")]'):
                bill_url = row.xpath('.//a[contains(@href,"/billpdf/")]/@href')[0]
                event.add_document(bill_title, bill_url, media_type="application/pdf")

            self.events[com][when_slug] = event

        for com in self.events:
            for date in self.events[com]:
                yield self.events[com][date]
