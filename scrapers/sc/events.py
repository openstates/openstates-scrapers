import re
import pytz
import datetime
import lxml.html

from openstates.scrape import Scraper, Event


def normalize_time(time_string):
    """
    Clean up and normalize the time_string obtained from the scraped page.
    :param time_string:
    :return:
    """
    time_string = time_string.lower().strip()
    if re.search(r"adjourn", time_string):
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


class SCEventScraper(Scraper):
    """
    Event scraper to pull down information regarding upcoming (or past) Events
    and associated metadata and any supporting material.
    """

    jurisdiction = "sc"
    _tz = pytz.timezone("US/Eastern")

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
        """
        Scrape the events data from all dates from the sc meetings page,
        then create and yield the events objects from the data.
        :param chamber:
        :param session:
        :return: yielded Event objects
        """

        chambers = {
            "upper": {"name": "Senate", "title": "Senator"},
            "lower": {"name": "House", "title": "Representative"},
        }
        if chamber == "other":
            return

        if chamber is None:
            self.info("no chamber specified, using Joint Committee Meeting Schedule")
            events_url = "http://www.scstatehouse.gov/meetings.php"
        else:
            events_url = "http://www.scstatehouse.gov/meetings.php?chamber=%s" % (
                chambers[chamber]["name"].upper()[0]
            )

        page = self.get_page_from_url(events_url)

        meeting_year = page.xpath('//h2[@class="barheader"]/span')[0].text_content()
        meeting_year = re.search(
            r"Week of [A-Z][a-z]+\s+[0-9]{1,2}, ([0-9]{4})", meeting_year
        ).group(1)

        dates = page.xpath("//div[@id='contentsection']/ul")

        for date in dates:
            date_string = date.xpath("span")

            if len(date_string) == 1:
                date_string = date_string[0].text_content()
            else:
                continue

            # If a event is in the next calendar year, the date_string
            # will have a year in it
            if date_string.count(",") == 2:
                event_year = date_string[-4:]
                date_string = date_string[:-6]
            elif date_string.count(",") == 1:
                event_year = meeting_year
            else:
                raise AssertionError("This is not a valid date: '{}'").format(
                    date_string
                )

            for meeting in date.xpath("li"):
                time_string = meeting.xpath("span")[0].text_content()
                status = "tentative"
                if (
                    time_string == "CANCELED"
                    or len(meeting.xpath('.//span[contains(text(), "CANCELED")]')) > 0
                ):
                    status = "cancelled"

                time_string = normalize_time(time_string)
                date_time = datetime.datetime.strptime(
                    event_year + " " + date_string + " " + time_string,
                    "%Y %A, %B %d %I:%M %p",
                )

                date_time = self._tz.localize(date_time)
                meeting_info = meeting.xpath("br[1]/preceding-sibling::node()")[1]
                location, description = re.search(
                    r"-- (.*?) -- (.*)", meeting_info
                ).groups()

                if re.search(r"committee", description, re.I):
                    classification = "committee-meeting"
                else:
                    classification = "other-meeting"

                event = Event(
                    name=description,  # Event Name
                    start_date=date_time,  # When the event will take place
                    location_name=location,
                    classification=classification,
                    status=status,
                )

                event.add_source(events_url)

                agenda_url = meeting.xpath(".//a[contains(@href,'agendas')]")

                if agenda_url:
                    agenda_url = agenda_url[0].attrib["href"]
                    event.add_source(agenda_url)
                    event.add_document(
                        note="Agenda", url=agenda_url, media_type="application/pdf"
                    )

                    if ".pdf" not in agenda_url:
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

                yield event
