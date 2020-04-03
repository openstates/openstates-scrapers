import datetime as dt
import lxml
import re

from openstates_core.scrape import Scraper, Event

import pytz

urls = {
    "upper": "http://www.ilga.gov/senate/schedules/weeklyhearings.asp",
    "lower": "http://www.ilga.gov/house/schedules/weeklyhearings.asp",
}


class IlEventScraper(Scraper):
    localize = pytz.timezone("America/Chicago").localize

    def scrape_page(self, url, session, chamber):
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
        for session in self.jurisdiction.legislative_sessions:
            session_id = session["identifier"]
            for chamber in ("upper", "lower"):

                try:
                    url = urls[chamber]
                except KeyError:
                    return  # Not for us.
                html = self.get(url).text
                doc = lxml.html.fromstring(html)
                doc.make_links_absolute(url)

                tables = doc.xpath("//table[@width='550']")
                for table in tables:
                    meetings = table.xpath(".//a")
                    for meeting in meetings:
                        event = self.scrape_page(
                            meeting.attrib["href"], session_id, chamber
                        )
                        yield event
