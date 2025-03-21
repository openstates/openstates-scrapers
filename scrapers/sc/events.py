import re
import pytz
import datetime
import lxml.html
from scrapelib import HTTPError

from openstates.scrape import Scraper, Event
from spatula import PdfPage, URL
from utils.events import match_coordinates


def normalize_time(time_string):
    """
    Clean up and normalize the time_string obtained from the scraped page.
    :param time_string:
    :return:
    """

    time_string = time_string.lower().strip()

    # Fix inconsistent formatting of pm/am
    time_string = time_string.replace("p.m.", "pm").replace("a.m.", "am")

    # replace "to XX:XX am|pm"
    time_string = re.sub(r"to \d{2}:\d{2} \w{2}", "", time_string).strip()
    if re.search(r"(upon|adjourn)", time_string):
        time_string = "12:00 am"
    if re.search(r" noon", time_string):
        time_string = time_string.replace(" noon", " pm")
    # remove extra spaces
    if re.search("[^ ]+ ?- ?[0-9]", time_string):
        start, end = re.search(r"([^ ]+) ?- ?([0-9])", time_string).groups()
        time_string = re.sub(start + " ?- ?" + end, start + "-" + end, time_string)
    # if it's a block of time, use the start time
    block_reg = re.compile(
        r"^([0-9]{1,2}:[0-9]{2}( [ap]m)?)-[0-9]{1,2}:[0-9]{2} ([ap]m)"
    )

    if re.search(block_reg, time_string):
        start_time, start_meridiem, end_meridiem = re.search(
            block_reg, time_string
        ).groups()

        start_hour = int(start_time.split(":")[0])
        if start_meridiem:
            time_string = re.search("^([0-9]{1,2}:[0-9]{2} [ap]m)", time_string).group(
                1
            )
        else:
            if end_meridiem == "pm" and start_hour < 12:
                time_string = start_time + " am"
            else:
                time_string = start_time + " " + end_meridiem
    return time_string


class Agenda(PdfPage):
    # Allow up to 3 non-alpha-numeric characters between letter and number poriton of bill id
    # Will correctly scrape bill ids like "H.123", "S(123)", "H - 0244", "S  43", "H. 55"
    bill_re = re.compile(r"(\W|^)(H|S)\W{0,3}0*(\d+)")

    def process_page(self):
        # Use a set to remove duplicate bill ids
        bill_ids = set()

        for _, alpha, num in self.bill_re.findall(self.text):
            # Format bill id and add it to the set
            bill_id = f"{alpha} {num}"
            bill_ids.add(bill_id)

        yield from bill_ids

    def process_error_response(self, exception):
        # Around 3/20/25 SC backend server seems to be timing out in serving docs
        # in browser seeing Cloudflare errors pointing at backend
        # Rather be able to get most events than totally fail scrape on this
        if isinstance(exception, HTTPError) and exception.response.status_code == 522:
            self.logger.warning(
                f"Unable to fetch PDF agenda doc {self.source}. Ignored error and continued."
            )
            pass
        else:
            raise exception


class SCEventScraper(Scraper):
    """
    Event scraper to pull down information regarding upcoming (or past) Events
    and associated metadata and any supporting material.
    """

    jurisdiction = "sc"
    _tz = pytz.timezone("US/Eastern")

    prior_event_time_string = None

    event_keys = set()

    def get_page_from_url(self, url):
        """
        Get page from the provided url and change to string
        :param url:
        :return:
        """
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    # def get_bill_description(self, url):
    #     """ Find and obtain bill description from bill page using xpath"""
    #     bill_page = self.get_page_from_url(url)
    #     bill_text = bill_page.xpath(
    #         './/div[@id="resultsbox"]/div[2]')[0]
    #     bill_description = bill_text.text_content().encode(
    #         'utf-8').split('\xc2\xa0\xc2\xa0\xc2\xa0\xc2\xa0')[0]

    #     bill_description = re.search(
    #         r'Summary: (.*)', bill_description).group(1).strip()
    #     return bill_description

    def get_stream_id(self, onclick: str) -> str:
        return re.findall(r"live_stream\((\d+)|$", onclick)[0]

    def scrape(self, chamber=None, session=None):
        if chamber:
            yield from self.scrape(chamber, session)
        else:
            yield from self.scrape_single_chamber("legislature", session)
            yield from self.scrape_single_chamber("upper", session)
            yield from self.scrape_single_chamber("lower", session)

    def scrape_single_chamber(self, chamber=None, session=None):
        """
        Scrape the events data from all dates from the sc meetings page,
        then create and yield the events objects from the data.
        :param chamber:
        :param session:
        :return: yielded Event objects
        """

        chambers = {
            "upper": "Senate",
            "lower": "House",
            "legislature": "Joint",
        }
        if chamber == "other":
            return

        if chamber is None:
            self.info("no chamber specified, using Joint Committee Meeting Schedule")
            events_url = "https://www.scstatehouse.gov/meetings.php"
        else:
            events_url = "https://www.scstatehouse.gov/meetings.php?chamber=%s" % (
                chambers[chamber].upper()[0]
            )
        page = self.get_page_from_url(events_url)

        meeting_year = page.xpath('//h2[@class="barheader"]/span')[0].text_content()
        meeting_year = re.search(
            r"Week of [A-Z][a-z]+\s+[0-9]{1,2}, ([0-9]{4})", meeting_year
        ).group(1)

        # Mostly each event is in a UL>LI, with date of event in UL>SPAN
        # But some ULs do not include a date SPAN
        # (subsequent ULs are on the same date, until a new date)
        date_string = ""
        dates = page.xpath("//div[@id='contentsection']/ul")

        for date in dates:
            date_elements = date.xpath("span")

            if len(date_elements) == 1:
                date_string = date_elements[0].text_content()

            # If an event is in the next calendar year, the date_string
            # will have a year in it
            if date_string.count(",") == 2:
                event_year = date_string[-4:]
                date_string = date_string[:-6]
            elif date_string.count(",") == 1:
                event_year = meeting_year
            else:
                raise AssertionError(f"This is not a valid date: '{date_string}'")

            for meeting in date.xpath("li"):
                time_string = meeting.xpath("span")[0].text_content()
                status = "tentative"
                if (
                    time_string == "CANCELED"
                    or len(meeting.xpath('.//span[contains(text(), "CANCELED")]')) > 0
                ):
                    status = "cancelled"

                # For cases when time string is listed as a reference to prior
                #  event's start time:
                #   i.e. "Immediately after EOC full committee"
                if "after" in time_string:
                    time_string = self.prior_event_time_string

                # Set attribute to be used for following event, as above case
                self.prior_event_time_string = time_string

                time_string = normalize_time(time_string)
                try:
                    date_time = datetime.datetime.strptime(
                        f"{event_year} {date_string} {time_string}",
                        "%Y %A, %B %d %I:%M %p",
                    )
                # if we can't parse the time due to manual additions, just set the day
                except ValueError:
                    self.warning(f"Unable to parse time string {time_string}")
                    date_time = datetime.datetime.strptime(
                        f"{event_year} {date_string}", "%Y %A, %B %d"
                    )

                date_time = self._tz.localize(date_time)

                try:
                    meeting_info = meeting.xpath("br[1]/preceding-sibling::node()")[1]
                    location, description = re.search(
                        r"-- (.*?) -- (.*)", meeting_info
                    ).groups()
                except Exception:
                    meeting_info = meeting.xpath("br[2]/preceding-sibling::node()")[4]
                    location, description = re.search(
                        r"(.*?) -- (.*)", meeting_info
                    ).groups()

                if re.search(r"committee", description, re.I):
                    classification = "committee-meeting"
                else:
                    classification = "other-meeting"

                description = re.sub(" on$", "", description.strip())
                event_key = f"{description}#{location}#{date_time}"

                if event_key in self.event_keys:
                    continue
                else:
                    self.event_keys.add(event_key)

                location = location.replace(
                    "Blatt",
                    "Blatt Building, 1105 Pendleton St, Columbia, SC 29201",
                    1,
                )
                location = location.replace(
                    "Gressette",
                    "Gressette Building, 1101 Pendleton St, Columbia, SC 29201",
                    1,
                )
                location = location.replace(
                    "State House",
                    "South Carolina State House, 1100 Gervais St, Columbia, SC 29208",
                    1,
                )

                event = Event(
                    name=description,  # Event Name
                    start_date=date_time,  # When the event will take place
                    location_name=location,
                    classification=classification,
                    status=status,
                )

                event.dedupe_key = event_key

                if "committee" in description.lower():
                    event.add_participant(description, type="committee", note="host")

                event.add_source(events_url)

                agenda_url = meeting.xpath(".//a[contains(@href,'agendas')]")

                if agenda_url:
                    agenda_url = agenda_url[0].attrib["href"]
                    event.add_source(agenda_url)
                    event.add_document(
                        note="Agenda", url=agenda_url, media_type="application/pdf"
                    )

                    if ".pdf" in agenda_url:
                        for bill_id in Agenda(source=URL(agenda_url)).do_scrape():
                            event.add_bill(bill_id)
                    else:
                        agenda_page = self.get_page_from_url(agenda_url)
                        for bill in agenda_page.xpath(
                            ".//a[contains(@href,'billsearch.php')]"
                        ):
                            # bill_url = bill.attrib['href']
                            bill_id = (
                                bill.text_content().replace(".", "").replace(" ", "")
                            )
                            # bill_description = self.get_bill_description(bill_url)

                            event.add_bill(bill_id)

                for row in meeting.xpath(".//a[text()='Live Broadcast']"):
                    stream_id = self.get_stream_id(row.xpath("@onclick")[0])
                    if not stream_id:
                        self.warning("Unable to extract stream id")
                        continue

                    event.add_media_link(
                        "Video Stream",
                        f"https://www.scstatehouse.gov/video/stream.php?key={stream_id}&audio=0",
                        media_type="text/html",
                    )

                for row in meeting.xpath(".//a[text()='Live Broadcast - Audio Only']"):
                    stream_id = self.get_stream_id(row.xpath("@onclick")[0])
                    if not stream_id:
                        self.warning("Unable to extract stream id")
                        continue

                    event.add_media_link(
                        "Audio Stream",
                        f"https://www.scstatehouse.gov/video/stream.php?key={stream_id}&audio=1",
                        media_type="text/html",
                    )

                match_coordinates(
                    event,
                    {
                        "Blatt Building": ("33.99860", "-81.03323"),
                        "Gressette Building": ("33.99917", "-81.03306"),
                        "State House": ("34.00028", "-81.032954"),
                    },
                )

                yield event
