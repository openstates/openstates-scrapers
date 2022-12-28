import pytz
import dateutil.parser
import datetime
import re

from utils import LXMLMixin
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

# http://mgaleg.maryland.gov/mgawebsite/Meetings/Day/0128202102282021?budget=show&cmte=allcommittees&updates=show&ys=2021rs


class MDEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Eastern")
    chambers = {"upper": "Senate", "lower": ""}
    date_format = "%m%d%Y"

    def scrape(self, session=None, start=None, end=None):
        if start is None:
            start_date = datetime.datetime.now().strftime(self.date_format)
        else:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
            start_date = start_date.strftime(self.date_format)

        # default to 60 days if no end
        if end is None:
            dtdelta = datetime.timedelta(days=60)
            end_date = datetime.datetime.now() + dtdelta
            end_date = end_date.strftime(self.date_format)
        else:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
            end_date = end_date.strftime(self.date_format)

        # regular gets an RS at the end, special gets nothing because s1 is in the session
        if session[-2] != "s":
            session += "rs"

        url = "https://mgaleg.maryland.gov/mgawebsite/Meetings/Day/{}{}?budget=show&cmte=allcommittees&updates=show&ys={}"
        url = url.format(start_date, end_date, session)

        page = self.lxmlize(url)

        # if both "<house banner> No Hearings Message" and "<senate banner> No Hearings Message"
        empty_chamber = "//div[div/div[contains(@class,'{chamber}')]]/following-sibling::text()[contains(.,'No hearings')]"
        if page.xpath(empty_chamber.format(chamber="Senate")) and page.xpath(
            empty_chamber.format(chamber="House")
        ):
            raise EmptyScrape
        event_count = 0

        for row in page.xpath('//div[@id="divAllHearings"]/hr'):
            banner = row.xpath(
                'preceding-sibling::div[contains(@class,"row")]/div/div[contains(@class,"hearsched-committee-banner")]'
            )[-1]
            banner_class = banner.xpath("@class")[0]
            chamber = ""
            if "house" in banner_class:
                chamber = "Assembly"
            elif "senate" in banner_class:
                chamber = "Senate"

            meta = row.xpath(
                'preceding-sibling::div[contains(@class,"hearsched-hearing-header")]'
            )[-1]
            data = row.xpath('preceding-sibling::div[contains(@class,"row")]')[-1]

            when = meta.xpath(
                './/div[contains(@class,"font-weight-bold text-center")]/text()'
            )[0].strip()

            com_row = meta.xpath(
                './/div[contains(@class,"font-weight-bold text-center")]/text()'
            )[1].strip()

            if chamber != "":
                com_row = f"{chamber} {com_row}"

            # if they strike all the header rows, its cancelled
            unstruck_count = len(
                meta.xpath(
                    './/div[contains(@class,"font-weight-bold text-center") and(not(contains(@class,"hearsched-strike")))]'
                )
            )
            if unstruck_count == 0:
                self.info(f"Skipping {com_row} {when} -- it appears cancelled")
                continue

            # find the first unstruck time row
            time_loc = meta.xpath(
                './/div[contains(@class,"font-weight-bold text-center")'
                'and(contains(text(),"AM") or contains(text(),"PM")) and(not(contains(@class,"hearsched-strike")))]/text()'
            )[0].strip()

            if "-" in time_loc:
                time = time_loc.split("-")[0].strip()
                where = time_loc.split("-")[1].strip()
            else:
                time = time_loc
                where = "See Committee Site"

            if com_row == "":
                continue

            # remove end dates
            when = re.sub(r"to \d+:\d+\s*\w+", "", f"{when} {time}").strip()
            when = dateutil.parser.parse(when)
            when = self._tz.localize(when)

            event = Event(
                name=com_row,
                location_name=where,
                start_date=when,
                classification="committee-meeting",
            )

            com_name = re.sub(r"[\s\-]*Work Session", "", com_row)
            event.add_participant(name=com_name, type="committee", note="host")

            event.add_source("https://mgaleg.maryland.gov/mgawebsite/Meetings/Week/")

            for agenda_row in data.xpath(
                "div/div/div[contains(@class,'hearsched-table')]"
            ):
                children = agenda_row.xpath("div")
                # bill row
                if len(children) == 4:
                    if agenda_row.xpath("div[1]/a"):
                        agenda = event.add_agenda_item(
                            agenda_row.xpath("div[4]/text()")[0].strip()
                        )
                        bill_num = agenda_row.xpath("div[1]/a/text()")[0].strip()
                        agenda.add_bill(bill_num)
                elif len(children) == 1:
                    agenda = event.add_agenda_item(
                        agenda_row.xpath("div[1]")[0].text_content().strip()
                    )
            event_count += 1
            yield event

        if event_count < 1:
            raise EmptyScrape
