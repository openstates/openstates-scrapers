import pytz
import cloudscraper
import dateutil.parser
import lxml.html
from openstates.scrape import Scraper, Event


class INEventScraper(Scraper):
    _tz = pytz.timezone("America/Indianapolis")
    # avoid cloudflare blocks for no UA
    cf_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
    }
    scraper = cloudscraper.create_scraper()

    def scrape(self):
        list_url = "http://iga.in.gov/legislative/2021/committees/standing"
        page = self.scraper.get(list_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(list_url)

        for com_row in page.xpath('//li[contains(@class,"committee-item")]/a/@href'):
            yield from self.scrape_committee_page(com_row)

    def scrape_committee_page(self, url):
        page = self.scraper.get(url, headers=self.cf_headers).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        com = page.xpath('//div[contains(@class, "pull-left span8")]/h1/text()')[
            0
        ].strip()

        for row in page.xpath('//div[contains(@id, "agenda-item")]'):
            meta = row.xpath('div[contains(@class,"accordion-heading-agenda")]/a')[0]

            date = meta.xpath("text()")[0].strip()

            time_and_loc = meta.xpath("span/text()")[0].strip()
            time_and_loc = time_and_loc.split("\n")
            time = time_and_loc[0]
            loc = time_and_loc[1]

            if loc == "":
                loc = "See Agenda"

            com = com.replace("(S)", "Senate").replace("(H)", "House")

            # Indiana has a LOT of undefined times, stuff like "15 mins after adj. of elections"
            # so just remove the time component if it won't parse, and the user can go to the agenda
            try:
                when = dateutil.parser.parse(f"{date} {time}")
            except dateutil.parser._parser.ParserError:
                when = dateutil.parser.parse(date)
            when = self._tz.localize(when)

            if "cancelled" in time.lower():
                continue

            event = Event(
                name=com,
                start_date=when,
                location_name=loc,
                classification="committee-meeting",
            )

            event.add_source(url)
            event.add_participant(com, type="committee", note="host")

            if row.xpath('.//a[contains(text(), "View Agenda")]'):
                agenda_url = row.xpath('.//a[contains(text(), "View Agenda")]/@href')[0]
                event.add_document("Agenda", agenda_url, media_type="application/pdf")

            if row.xpath('.//a[contains(text(), "Watch")]'):
                vid_url = row.xpath('.//a[contains(text(), "Watch")]/@href')[0]
                event.add_media_link(
                    "Video of Hearing", vid_url, media_type="text/html"
                )

            if row.xpath('.//tr[contains(@class,"bill-container")]/td'):
                agenda = event.add_agenda_item("Bills under consideration")
                for bill_row in row.xpath('.//tr[contains(@class,"bill-container")]'):
                    bill_id = bill_row.xpath(
                        ".//a[contains(@class,'bill-name-link')]/text()"
                    )[0]
                    agenda.add_bill(bill_id)

            yield event
