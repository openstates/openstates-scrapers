import re
import datetime as dt

import pytz
from openstates_core.scrape import Scraper, Event

from scrapers.utils import LXMLMixin

url = "http://assembly.state.ny.us/leg/?sh=hear"


class NYEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Eastern")

    def lower_parse_page(self, url):
        page = self.lxmlize(url)
        tables = page.xpath("//table[@class='pubhrgtbl']")
        date = None
        for table in tables:
            metainf = {}
            rows = table.xpath(".//tr")
            for row in rows:
                tds = row.xpath("./*")
                if len(tds) < 2:
                    continue
                key, value = tds

                if key.tag == "th" and key.get("class") == "hrgdate":
                    date = key.text_content()
                    date = re.sub(r"\s+", " ", date)
                    date = re.sub(".*POSTPONED NEW DATE", "", date).strip()

                # Due to the html structure this shouldn't be an elif
                # It needs to fire twice in the same loop iteration
                if value.tag == "th" and value.get("class") == "commtitle":
                    coms = value.xpath('.//div[contains(@class,"comm-txt")]/text()')

                elif key.tag == "td":
                    key = key.text_content().strip()
                    value = value.text_content().strip()
                    value = value.replace(u"\x96", "-")
                    value = re.sub(r"\s+", " ", value)
                    metainf[key] = value

            time = metainf["Time:"]
            repl = {"A.M.": "AM", "P.M.": "PM"}
            drepl = {"Sept": "Sep"}
            for r in repl:
                time = time.replace(r, repl[r])

            for r in drepl:
                date = date.replace(r, drepl[r])

            time = re.sub("-.*", "", time)
            time = time.strip()

            year = dt.datetime.now().year

            date = "%s %s %s" % (date, year, time)

            if "tbd" in date.lower():
                continue

            date = date.replace(" PLEASE NOTE NEW TIME", "")

            # Check if the event has been postponed.
            postponed = "POSTPONED" in date
            if postponed:
                date = date.replace(" POSTPONED", "")

            date_formats = ["%B %d %Y %I:%M %p", "%b. %d %Y %I:%M %p"]
            datetime = None
            for fmt in date_formats:
                try:
                    datetime = dt.datetime.strptime(date, fmt)
                except ValueError:
                    pass

            # If the datetime can't be parsed, bail.
            if datetime is None:
                return

            title_key = set(metainf) & set(
                [
                    "Public Hearing:",
                    "Summit:",
                    "Roundtable:",
                    "Public Roundtable:",
                    "Public Meeting:",
                    "Public Forum:",
                    "Meeting:",
                ]
            )
            assert len(title_key) == 1, "Couldn't determine event title."
            title_key = list(title_key).pop()
            title = metainf[title_key]

            title = re.sub(
                r"\*\*Click here to view public hearing notice\*\*", "", title
            )

            # If event was postponed, add a warning to the title.
            if postponed:
                title = "POSTPONED: %s" % title

            event = Event(
                name=title,
                start_date=self._tz.localize(datetime),
                location_name=metainf["Place:"],
            )
            event.extras = {"contact": metainf["Contact:"]}
            if "Media Contact:" in metainf:
                event.extras.update(media_contact=metainf["Media Contact:"])
            event.add_source(url)

            for com in coms:
                event.add_participant(com.strip(), type="committee", note="host")
                participant = event.participants[-1]
                participant["extras"] = ({"chamber": self.classify_committee(com)},)

            yield event

    def scrape(self):
        yield from self.lower_parse_page(url)

    def classify_committee(self, name):
        chamber = "other"
        if "senate" in name.lower():
            chamber = "upper"
        if "assembly" in name.lower():
            chamber = "lower"
        if "joint" in name.lower():
            chamber = "joint"
        return chamber
