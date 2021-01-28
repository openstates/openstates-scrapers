from openstates.scrape import Scraper, Event
from dateutil import parser, relativedelta
import datetime
import lxml
import pytz


class MTEventScraper(Scraper):
    _tz = pytz.timezone("America/Denver")
    base_url = "http://laws.leg.mt.gov/"

    def scrape(self, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using latest")

        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                session_slug = i["_scraped_name"]


        url = "http://laws.leg.mt.gov/legprd/LAW0240W$CMTE.ActionQuery?P_SESS={session_slug}&P_COM_NM=&P_ACTN_DTM={start}&U_ACTN_DTM={end}&Z_ACTION2=Find"

        start = datetime.datetime.today()
        # this month and the next 2 months
        end = start + relativedelta.relativedelta(months=+2)

        url = url.format(
            session_slug = session_slug,
            start = start.strftime('%m/01/%Y'),
            end = end.strftime('%m/%d/%Y')
        )

        page = self.get(url).content
        page = lxml.html.fromstring(page)

        for row in page.xpath('//table[@border]/tr'):
            # skip table headers
            if not row.xpath('td[1]/a'):
                continue
            day = row.xpath("td[2]/text()")[0].strip()
            time = row.xpath("td[3]/text()")[0].strip()
            room = row.xpath("td[4]")[0].text_content().strip()
            bill = row.xpath("td[5]/a[1]/text()")[0].strip()

            com = row.xpath('td[1]/a[1]/text()')[0].strip()
            com = com.replace('(H)', 'House').replace('(S)', 'Senate')

            print(com, day, time, room, bill)

        yield {}