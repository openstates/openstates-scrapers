import pytz
import datetime
import dateutil.parser
import re
from .util import get_token
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

from spatula import URL, PdfPage


class GAEventScraper(Scraper):
    # usage:
    #  PYTHONPATH=scrapers poetry run os-update ga events --scrape start=YYYY-mm-dd
    tz = pytz.timezone("US/Eastern")

    def scrape(self, start=None):
        if start is None:
            start = datetime.datetime.today()
        else:
            start = datetime.datetime.strptime(start, "%Y-%m-%d")

        date_format = "%a %b %d %Y"
        date_slug = start.strftime(date_format)

        url = f"https://www.legis.ga.gov/api/meetings?startDate={date_slug}"

        page = self.get(url, headers={"Authorization": get_token()}).json()
        event_count = 0

        if len(page) == 0:
            raise EmptyScrape

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

            if row["agendaUri"]:
                # fix a typo
                row["agendaUri"] = row["agendaUri"].replace("https/", "https://")
                event.add_document(
                    "Agenda", row["agendaUri"], media_type="application/pdf"
                )
                event.dedupe_key = row["agendaUri"]
                # Scrape bill ids from agenda pdf
                try:
                    for bill_id in Agenda(source=URL(row["agendaUri"])).do_scrape():
                        event.add_bill(bill_id)
                except Exception as e:
                    self.warning(f"{row['agendaUri']} failed to scrape: {e}")
                    pass

            if row["livestreamUrl"]:
                event.add_media_link(
                    "Video", row["livestreamUrl"], media_type="text/html"
                )

            if "committee" in title.lower():
                com = re.sub(r"\(.*\)", "", title)
                event.add_committee(com)

            event.add_source("https://www.legis.ga.gov/schedule/all")
            event_count += 1
            yield event

        if event_count == 0:
            raise EmptyScrape


class Agenda(PdfPage):
    non_formatted_re = re.compile(r"(H|S).+(B|R).+\s+(\d+)")

    def process_page(self):
        matches = re.findall(
            r"((SB|HB|SR|HR|House Bill|Senate Bill|House Resolution"
            r"|Senate Resolution|H\.B\.|S\.B\.|H\.R\.|S\.R\.)\s+\d+)",
            self.text,
        )
        for m, _ in matches:
            yield self.format_match(m)

    def format_match(self, match):
        needs_formatting = self.non_formatted_re.search(match)
        if not needs_formatting:
            return match
        else:
            chamber, bill_type, num = needs_formatting.groups()
            return f"{chamber}{bill_type} {num}"
