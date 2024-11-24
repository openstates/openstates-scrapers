import datetime as dt

from openstates.scrape import Event, Scraper
from utils import LXMLMixin, url_xpath
from utils.events import match_coordinates
from spatula import HtmlPage, URL, XPath, SelectorError, PdfPage

import dateutil
import pytz
import re


cal_weekly_events = "http://wapp.capitol.tn.gov/apps/schedule/WeeklyView.aspx"
cal_chamber_text = {"upper": "Senate", "lower": "House", "other": "Joint"}

bill_id_re = re.compile(r"(SJR|HB|HR|SB|HJR|SR)\s{0,3}0*(\d+)")


def scrape_bills(text):
    bills = set()
    for alpha, num in bill_id_re.findall(text):
        bills.add(f"{alpha} {num}")
    return list(bills)


# Yields all bill ids found on an html page. If the page contains a table with
# links to other pages, recursively calls itself and yields all bill ids on those
# pages.
class AgendaHtml(HtmlPage):
    example_source = "https://wapp.capitol.tn.gov/apps/videocalendars/VideoCalendarOrders.aspx?CalendarID=30415&GA=113"

    def process_page(self):
        try:
            # The page contains a table of links to other pages that contain bills
            pages = XPath("//*[@id='generatedcontent']/table/tr/td/a").match(self.root)
            for page in pages:
                # Skip floor session
                if "floor" in page.text_content().lower():
                    continue
                yield from AgendaHtml(source=URL(page.get("href"))).do_scrape()

        except SelectorError:
            # The page contains a list of bills and has
            # invalid html e.g. "<li ID='HB1197' <p><b>"
            # so regex is used to find the bill ids
            yield from scrape_bills(self.root.text_content())


# Yields all bill ids found in a PDF
class AgendaPdf(PdfPage):
    def process_page(self):
        yield from scrape_bills(self.text)


class TNEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Central")
    _utc = pytz.timezone("UTC")
    _tzmapping = {"CST": "US/Central"}

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber()

    def scrape_chamber(self, chamber=None):
        # If chamber is None, don't exclude any events from the results based on chamber
        chmbr = cal_chamber_text.get(chamber)

        cal_urls = [cal_weekly_events]
        today = dt.date.today()
        for i in range(1, 12):
            date = today + dt.timedelta(days=7 * i)
            date_str = date.strftime("%m/%d/%Y")
            cal_url = f"{cal_weekly_events}?date={date_str}"
            cal_urls.append(cal_url)

        for cal_url in cal_urls:
            self.info(cal_url)
            tables = url_xpath(cal_url, "//table[@class='date-table']")
            for table in tables:
                date = table.xpath("../.")[0].getprevious().text_content()
                trs = table.xpath("./tr")
                for tr in trs:
                    order = ["time", "chamber", "type", "agenda", "location", "video"]

                    tds = tr.xpath("./td")
                    metainf = {}

                    if not tds:
                        continue

                    for el in range(0, len(order)):
                        metainf[order[el]] = tds[el]

                    if chmbr and metainf["chamber"].text_content() != chmbr:
                        self.info("Skipping event based on chamber.")
                        continue

                    # Skip floor session
                    if "floor" in metainf["type"].text_content().lower():
                        continue

                    time = metainf["time"].text_content()
                    datetime_string = "%s %s" % (
                        date.strip(" \r\n"),
                        time.strip(" \r\n"),
                    )
                    location = metainf["location"].text_content()

                    if re.match(
                        r"^house hearing room", location, flags=re.I
                    ) or re.match(r"^[house|senate] chamber", location, flags=re.I):
                        location = f"{location}, 600 Dr. Martin L King, Jr. Blvd, Nashville, TN 37243"

                    description = metainf["type"].text_content()
                    # skipping cancelled here instead of setting a status, because
                    # they clear the time on canceled events so we can't look them up
                    if time == "Cancelled":
                        self.log("Skipping cancelled event.")
                        continue
                    else:
                        if "Immediately follows H-FLOOR" in datetime_string:
                            continue
                        if " Immediately follows" in datetime_string:
                            datetime_string, _ = datetime_string.split(
                                "Immediately follows"
                            )
                        if "canceled" in datetime_string.lower():
                            continue
                        if "TBA" in datetime_string:
                            continue

                        datetime_string = datetime_string.strip()
                        when = dateutil.parser.parse(
                            datetime_string, tzinfos=self._tzmapping
                        )
                        if when.tzinfo is None:
                            when = self._tz.localize(when)

                    event = Event(
                        name=description,
                        start_date=when,
                        location_name=location,
                        description=description,
                    )
                    # The description is a committee name
                    event.add_committee(name=description)
                    event.add_source(cal_url)

                    agenda = metainf["agenda"].xpath(".//a")
                    for doc in agenda:
                        agenda_url = doc.attrib["href"]
                        if agenda_url.endswith(".pdf"):
                            event.add_document(
                                "Agenda",
                                agenda_url,
                                media_type="application/pdf",
                                on_duplicate="ignore",
                            )
                            for bill in AgendaPdf(source=agenda_url).do_scrape():
                                event.add_bill(bill)
                        else:
                            event.add_document(
                                "Agenda",
                                agenda_url,
                                media_type="text/html",
                                on_duplicate="ignore",
                            )
                            event.dedupe_key = re.search(
                                r"ID=(\d*)&", agenda_url
                            ).group(1)
                            for bill in AgendaHtml(source=agenda_url).do_scrape():
                                event.add_bill(bill)

                    match_coordinates(event, {"600 Dr. Martin": (36.16633, -86.78418)})

                    yield event
