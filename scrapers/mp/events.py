import cloudscraper
import dateutil
import lxml
import pytz
import re

from openstates.scrape import Scraper, Event


class MPEventScraper(Scraper):
    _tz = pytz.timezone("Pacific/Saipan")
    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    }

    # transform
    # MM_openBrWindow('calendar_event.asp?calID=7763','','scrollbars=yes,width=400,height=400')
    # to https://cnmileg.net/calendar_event.asp?calID=7763
    def extract_url(self, path: str) -> str:
        matches = re.findall(r"\'(.*?)\'", path)
        return f"https://cnmileg.net/{matches[0]}"

    # transform "10:30 a.m. - CHCC BOARD OF TRUSTEES" into "10:30 a.m."
    def extract_time(self, timestring: str) -> str:
        matches = re.findall(r"\d+:\d+\s*[apm\.]*", timestring, flags=re.IGNORECASE)
        return matches[0]

    def scrape(self):
        data = {
            "subPrev.x": "14",
            "subPrev.y": "10",
            "CURDATE_month": "October",
            "CURDATE_YEAR": "2023",
            "CURDATE": "10/1/2023",
        }
        page = self.scraper.post("https://cnmileg.net/calendar.asp", data=data).content

        page = lxml.html.fromstring(page)

        for a in page.xpath("//ul/li/a[contains(@class,'eventlnk')]"):
            path = a.xpath("@onclick")[0]
            url = self.extract_url(path)
            yield from self.scrape_page(url)

    def scrape_page(self, url):
        self.info(f"GET {url}")
        page = self.scraper.get(url).content
        page = lxml.html.fromstring(page)

        page.make_links_absolute(url)

        start = page.xpath("//h4[1]/text()")[0]
        title = page.xpath("//h5[1]/text()")[0]
        time = page.xpath("//p[contains(text(), 'Time:')]/text()")[0]
        time = time.replace("Time:", "").strip()
        time = self.extract_time(time)

        start = dateutil.parser.parse(f"{start} {time}")
        start = self._tz.localize(start)

        location = page.xpath("//p[contains(text(), 'Location:')]/text()")[0]
        location = location.replace("Location:", "").strip()

        print(start, title, time, location)

        event = Event(title, start, location)

        for doc in page.xpath("//a[contains(@href, '.pdf')]"):
            event.add_document(
                doc.xpath("text()")[0],
                doc.xpath("@href")[0],
                media_type="application/pdf",
                on_duplicate="ignore",
            )

        event.add_source(url)
        yield event
