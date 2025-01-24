import datetime
import dateutil.parser
import lxml
import pytz

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape


class KSEventScraper(Scraper):
    tz = pytz.timezone("America/Chicago")
    date_range = 30

    def scrape(self, session, start=None):
        self.headers[
            "User-Agent"
        ] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
        now = datetime.datetime.now()
        if start is None:
            start = now - datetime.timedelta(days=self.date_range)
        else:
            start = dateutil.parser.parse(start)

        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        slug = meta["_scraped_name"]

        # ending slash matters...
        url_root = f"http://www.kslegislature.org/li/{slug}/committees/hearings/"

        event_count = 0
        events = set()
        for delta in range(self.date_range * 2):
            date = (start + datetime.timedelta(days=delta)).strftime("%m/%d/%Y")
            url = f"{url_root}?selected_date={date}"
            page = self.get(url).content
            page = lxml.html.fromstring(page)
            """
            Headers for each day look like
            Committee 	Chamber 	Bill 	Short Title 	Time 	Room 	Status
            """
            for hearing in page.xpath("//table[@id='hearingsTable']/tbody/tr"):
                columns = hearing.xpath("td")
                com_name = columns[0].xpath("a")[0].text.strip()
                com_link = f"http://www.kslegislature.org/{columns[0].xpath('a')[0].attrib['href']}"
                chamber = columns[1].xpath("a")[0].text.strip()
                try:
                    bill_id = columns[2].xpath("a")[0].text.strip()
                    bill_link = f"http://www.kslegislature.org/{columns[2].xpath('a')[0].attrib['href']}"
                except Exception:
                    bill_link = None
                    bill_id = None
                    self.warning(f"{hearing} missing bill details")
                    pass
                title = columns[3].text.strip()
                time = columns[4].text.strip()
                when = self.tz.localize(dateutil.parser.parse(f"{date} {time}"))
                location = columns[5].text.strip()
                if location == "":
                    location = "Not listed"
                event_name = f"{chamber}#{com_name}#{title}#{when}"[:500]
                if event_name in events:
                    self.warning(f"Skipping duplicate event {event_name}")
                    continue
                events.add(event_name)
                event = Event(
                    start_date=when,
                    name=f"{chamber} {com_name}",
                    location_name=location,
                )
                event.dedupe_key = event_name[:499]
                event.add_participant(
                    f"{chamber} {com_name}", type="committee", note="host"
                )
                event.add_source(url)
                event.add_source(com_link)
                agenda = None
                if title:
                    agenda = event.add_agenda_item(title)
                if bill_link:
                    event.add_source(bill_link)
                if bill_id and agenda:
                    agenda.add_bill(bill_id)
                event_count += 1
                yield event
        if event_count < 1:
            raise EmptyScrape
