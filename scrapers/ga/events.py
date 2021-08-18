import pytz
import datetime
import dateutil.parser
import re
import time
import requests
from hashlib import sha512
from openstates.scrape import Scraper, Event


class GAEventScraper(Scraper):
    # usage:
    #  PYTHONPATH=scrapers poetry run os-update ga events --scrape start=YYYY-mm-dd
    tz = pytz.timezone("US/Eastern")

    def get_key(timestamp):
        part1 = "QFpCwKfd7"
        part2 = "fjVEXFFwSu36BwwcP83xYgxLAhLYmKk"
        part3 = "letvarconst"
        key = part1 + part2 + part3 + timestamp
        return sha512(key.encode()).hexdigest()

    def get_token():
        timestamp = str(int(time.time() * 1000))
        key = GAEventScraper.get_key(timestamp)
        token_url = f"https://www.legis.ga.gov/api/authentication/token?key={key}&ms={timestamp}"
        return "Bearer " + requests.get(token_url).json()

    def scrape(self, start=None):
        if start is None:
            start = datetime.datetime.today()
        else:
            start = datetime.datetime.strptime(start, "%Y-%m-%d")

        date_format = "%a %b %d %Y"
        date_slug = start.strftime(date_format)

        url = f"https://www.legis.ga.gov/api/meetings?startDate={date_slug}"
        token = GAEventScraper.get_token()
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.legis.ga.gov/schedule/all",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/92.0.4515.131 Safari/537.36",
            "Authorization": token,
        }

        page = self.get(url, headers=headers).json()

        for row in page:
            status = "tentative"

            title = row["subject"]

            if "joint" not in title.lower():
                if row["chamber"] == 2:
                    title = f"Senate {title}"
                elif row["chamber"] == 1:
                    title = f"House {title}"

            start = dateutil.parser.parse(row["start"])

            if start < self.tz.localize(datetime.datetime.now()):
                status = "passed"

            if "cancelled" in title.lower() or "canceled" in title.lower():
                status = "cancelled"
                # try to replace all variants of "[optional dash] cancel[l]ed [optional dash]"
                # so we can match up events to their pre-cancellation occurrence
                title = re.sub(r"-?\s*cancell?ed\s*-?\s*", " ", title, flags=re.I)

            where = row["location"]
            where = f"206 Washington St SW, Atlanta, Georgia, {where}"

            event = Event(
                name=title,
                start_date=start,
                location_name=where,
                classification="committee-meeting",
                status=status,
            )

            if row["agendaUri"] != "":
                event.add_document(
                    "Agenda", row["agendaUri"], media_type="application/pdf"
                )

            if row["livestreamUrl"] is not None:
                event.add_media_link(
                    "Video", row["livestreamUrl"], media_type="text/html"
                )

            event.add_source("https://www.legis.ga.gov/schedule/all")

            yield event
