import datetime
import lxml
import pytz
import re


from openstates.scrape import Scraper, Event


class NEEventScraper(Scraper):
    _tz = pytz.timezone("US/Central")

    # usage: PYTHONPATH=scrapers poetry run os-update ne 
    # events --scrape start=2020-02-02 end=2020-03-02
    # or left empty it will default to the next 30 days
    def scrape(self, start=None, end=None):
        LIST_URL = "https://nebraskalegislature.gov/calendar/hearings_range.php"

        now = datetime.datetime.now()
        print_format = "%Y-%m-%d"

        if start is None:
            start = now
        else:
            start = datetime.datetime.strptime(start, "%Y-%m-%d")

        if end is None:
            end = now + datetime.timedelta(days=30)
        else:
            end = datetime.datetime.strptime(end, "%Y-%m-%d")

        args = {
            "startMonth": start.strftime("%m"),
            "startDay": start.strftime("%d"),
            "startYear": start.strftime("%Y"),
            "endMonth": end.strftime("%m"),
            "endDay": end.strftime("%d"),
            "endYear": end.strftime("%Y"),
        }
        page = self.post(LIST_URL, args).content

        yield from self.scrape_events(page)

    def scrape_events(self, page):

        page = lxml.html.fromstring(page)

        for meeting in page.xpath('//div[@class="card mb-4"]'):
            com = meeting.xpath('div[contains(@class, "card-header")]/text()')[
                0
            ].strip()
            details = meeting.xpath(
                'div[contains(@class, "card-header")]/small/text()'
            )[0].strip()

            (location, time) = details.split(" - ")

            # turn room numbers into the full address
            if location.lower().startswith("room"):
                location = "1445 K St, Lincoln, NE 68508, {}".format(location)

            day = meeting.xpath("./preceding-sibling::h2[@class='text-center']/text()")[
                -1
            ].strip()

            # Thursday February 27, 2020 1:30 PM
            date = "{} {}".format(day, time)
            event_date = self._tz.localize(
                datetime.datetime.strptime(date, "%A %B %d, %Y %I:%M %p")
            )

            event = Event(
                name=com,
                start_date=event_date,
                classification="committee-meeting",
                description="Committee Meeting",
                location_name=location,
            )

            event.add_committee(com, note="host")

            for row in meeting.xpath("div/table/tr"):
                agenda_desc = row.xpath("td[3]/text()")[0].strip()
                agenda_item = event.add_agenda_item(description=agenda_desc)

                if row.xpath("td[1]/a"):
                    # bill link
                    agenda_item.add_bill(row.xpath("td[1]/a/text()")[0].strip())

            event.add_source("https://nebraskalegislature.gov/calendar/calendar.php")

            yield event