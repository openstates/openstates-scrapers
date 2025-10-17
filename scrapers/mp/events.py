import cloudscraper
import datetime
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

    committee_regex = r"(?P<com>(Senate|House|Joint)\s*(Standing)?\s*Committee on (.*?))(Committee Meeting|Committee Public Hearing|Organization Meeting|Meeting|Public Hearing|Committee Press Conference)"

    # transform
    # MM_openBrWindow('calendar_event.asp?calID=7763','','scrollbars=yes,width=400,height=400')
    # to https://cnmileg.net/calendar_event.asp?calID=7763
    def extract_url(self, path: str) -> str:
        matches = re.findall(r"\'(.*?)\'", path)
        return f"https://cnmileg.net/{matches[0]}"

    # transform "10:30 a.m. - CHCC BOARD OF TRUSTEES" into "10:30 a.m."
    def extract_time(self, timestring: str) -> str:
        # 10: 00 am to 10:00 am
        timestring = timestring.replace(": ", "")
        matches = re.findall(r"\d+:\d+\s*[apm\.]*", timestring, flags=re.IGNORECASE)

        if "TBA" in timestring.upper():
            self.info(f"Skipping TBA event. {timestring}")
            return ""

        if len(matches) == 0:
            self.error(f"Could not parse timestring {timestring}")
            return ""

        return matches[0]

    def scrape(self):
        year = datetime.datetime.today().year

        # the curdate vars in the post request
        # are actually the first day of the
        # NEXT MONTH of the data you want to see.

        # 2 -> 12 will actually scrape
        # jan -> nov
        for month in range(2, 13):
            date = datetime.datetime(year, month, 1)
            yield from self.post_search(date)

        # jan if the next year will actually scrape dec of the previous
        yield from self.post_search(datetime.datetime(year + 1, 1, 1))

    def post_search(self, date: datetime.datetime):
        data = {
            "subPrev.x": "14",
            "subPrev.y": "10",
            "CURDATE_month": date.strftime("%B"),  # October
            "CURDATE_YEAR": date.year,
            "CURDATE": date.strftime("%m/%-d/%Y"),  # 10/1/2023
        }
        self.info("POST https://cnmileg.net/calendar.asp", data)
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
        if page.xpath("//p[contains(text(), 'Time:')]/text()"):
            time = page.xpath("//p[contains(text(), 'Time:')]/text()")[0]
            time = time.replace("Time:", "").strip()
        else:
            # my kingdom for xpath 2.0 in lxml, so we can do regex matches...
            time = page.xpath(
                "//p[contains(text(), 'a.m.') or contains(text(), 'p.m.') or contains(text(), 'A.M.') or contains(text(), 'P.M.')]/text()"
            )[0]

        time = self.extract_time(time)

        start = dateutil.parser.parse(f"{start} {time}")
        start = self._tz.localize(start)

        location = page.xpath(
            "//p[contains(text(), 'Location:') or contains(text(), 'LOCATION:')]/text()"
        )[0]
        location = location.replace("Location:", "").strip()

        event = Event(title, start, location)

        for doc in page.xpath("//a[contains(@href, '.pdf')]"):
            event.add_document(
                doc.xpath("text()")[0],
                doc.xpath("@href")[0],
                media_type="application/pdf",
                on_duplicate="ignore",
            )

        matches = re.findall(self.committee_regex, title, flags=re.IGNORECASE)

        if matches:
            com = matches[0][0].strip()
            event.add_participant(com, "committee")

        event.add_source(url)
        yield event
