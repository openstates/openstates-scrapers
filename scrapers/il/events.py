import datetime as dt
import lxml
import re

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

import pytz

BASE_URL = "https://ilga.gov"
urls = {
    "upper": f"{BASE_URL}/Senate/Schedules",
    "lower": f"{BASE_URL}/House/Schedules",
}

chamber_names = {
    "upper": "Senate",
    "lower": "House",
}

# Used to extract parts of bill id
bill_re = re.compile(r"(\w+?)\s*0*(\d+)")

# Used to remove prefixes from committee name
committee_name_re = re.compile(r"(.*) Hearing Details", flags=re.IGNORECASE)


class IlEventScraper(Scraper):
    localize = pytz.timezone("America/Chicago").localize

    def scrape_page(self, url, chamber):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        ctty_name = doc.xpath(
            '//*[@id="main-content"]/div[@id="copyable-content"]//h2'
        )[0].text_content()

        # Remove prefixes from the name like "Hearing notice for"
        ctty_name = committee_name_re.match(ctty_name).group(1)

        tables = doc.xpath(
            '//div[contains(@class, "card")][.//h4[contains(., "Hearing Details")]]//table'
        )
        if not tables:
            self.warning(f"Empty hearing data for {url}")
            return False, False
        info = tables[0]
        rows = info.xpath(".//tr")
        metainf = {}
        for row in rows:
            tds = "".join(row.xpath(".//td//text()")).split(":")
            key = tds[0].strip()
            value = ":".join(tds[1:]).strip()
            metainf[key] = value
        where = metainf["Location"]

        description = f"{chamber} {ctty_name}"
        # Remove committee suffix from names
        committee_suffix = " Committee"
        if description.endswith(committee_suffix):
            description = description[: -len(committee_suffix)]
        # Add spacing around hyphens
        if "-" in description:
            descr_parts = description.split("-")
            description = " - ".join([x.strip() for x in descr_parts])

        datetime = metainf["Date"]
        datetime = re.sub(r"\s+", " ", datetime)
        repl = {"AM": " AM", "PM": " PM"}  # Space shim.
        for r in repl:
            datetime = datetime.replace(r, repl[r])
        datetime = self.localize(dt.datetime.strptime(datetime, "%m/%d/%Y %I:%M %p"))

        event_name = f"{description}#{where}#{datetime}"
        event = Event(description, start_date=datetime, location_name=where)
        event.dedupe_key = event_name
        event.add_source(url)

        event.add_participant(ctty_name, "organization")

        bills = doc.xpath(
            '//div[contains(@class, "card")][.//h4[contains(., "Bills Assigned To Hearing")]]//table'
        )
        if bills:
            bills = bills[0]
            for bill in bills.xpath(".//tr")[1:]:
                tds = bill.xpath(".//td")
                if len(tds) < 4:
                    continue
                # First, let's get the bill ID:
                bill_id = tds[0].text_content()

                # Apply correct spacing to bill id
                (alpha, num) = bill_re.match(bill_id).groups()
                bill_id = f"{alpha} {num}"

                agenda_item = event.add_agenda_item(bill_id)
                agenda_item.add_bill(bill_id)

        return event, event_name

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

            if doc.xpath('//p[contains(text(), "No scheduled hearings for Month")]'):
                self.info(f"No hearings in {chamber}")
                no_scheduled_ct += 1
                continue

            tables = doc.xpath('//*[@id="pane-Month"]//table//tr')
            events = set()
            for table in tables:
                meetings = table.xpath(".//a[contains(@class, 'btn')]")
                for meeting in meetings:
                    meeting_url = meeting.attrib["href"]
                    event, name = self.scrape_page(meeting_url, chamber_names[chamber])
                    if event and name:
                        if name in events:
                            self.warning(f"Duplicate event {name}")
                            continue
                        events.add(name)
                        yield event

        if no_scheduled_ct == 2:
            raise EmptyScrape
