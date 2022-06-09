import datetime as dt
import lxml
import re

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

import pytz

urls = {
    "upper": "https://www.ilga.gov/senate/schedules/weeklyhearings.asp",
    "lower": "https://www.ilga.gov/house/schedules/weeklyhearings.asp",
}


class IlEventScraper(Scraper):
    localize = pytz.timezone("America/Chicago").localize

    def scrape_page(self, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        ctty_name = doc.xpath("//span[@class='heading']")[0].text_content()

        tables = doc.xpath("//table[@cellpadding='3']")
        info = tables[0]
        rows = info.xpath(".//tr")
        metainf = {}
        for row in rows:
            tds = row.xpath(".//td")
            key = tds[0].text_content().strip()
            value = tds[1].text_content().strip()
            metainf[key] = value

        where = metainf["Location:"]
        subject_matter = metainf["Subject Matter:"]
        description = "{}, {}".format(ctty_name, subject_matter)

        datetime = metainf["Scheduled Date:"]
        datetime = re.sub(r"\s+", " ", datetime)
        repl = {"AM": " AM", "PM": " PM"}  # Space shim.
        for r in repl:
            datetime = datetime.replace(r, repl[r])
        datetime = self.localize(dt.datetime.strptime(datetime, "%b %d, %Y %I:%M %p"))

        event = Event(description, start_date=datetime, location_name=where)
        event.add_source(url)

        if ctty_name.startswith("Hearing Notice For"):
            ctty_name.replace("Hearing Notice For", "")
        event.add_participant(ctty_name, "organization")

        bills = tables[1]
        for bill in bills.xpath(".//tr")[1:]:
            tds = bill.xpath(".//td")
            if len(tds) < 4:
                continue
            # First, let's get the bill ID:
            bill_id = tds[0].text_content()
            agenda_item = event.add_agenda_item(bill_id)
            agenda_item.add_bill(bill_id)

        return event

    def scrape(self):
        no_scheduled_ct = 0

        for chamber in ("upper", "lower"):

            try:
                url = urls[chamber]
            except KeyError:
                return  # Not for us.
            html = self.get(url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            if doc.xpath('//div[contains(text(), "No hearings currently scheduled")]'):
                self.info(f"No hearings in {chamber}")
                no_scheduled_ct += 1
                continue

            tables = doc.xpath("//table[@width='550']")
            for table in tables:
                meetings = table.xpath(".//a")
                for meeting in meetings:
                    event = self.scrape_page(meeting.attrib["href"])
                    yield event

        if no_scheduled_ct == 2:
            raise EmptyScrape
