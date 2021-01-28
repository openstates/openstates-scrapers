import pytz
import dateutil.parser
import datetime
import sys

from urllib.parse import urlsplit, parse_qs
from utils import LXMLMixin
from openstates.scrape import Scraper, Event

# http://mgaleg.maryland.gov/mgawebsite/Meetings/Day/0128202102282021?budget=show&cmte=allcommittees&updates=show&ys=2021rs

class MDEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Eastern")
    chambers = {"upper": "Senate", "lower": ""}
    date_format = "%m%d%Y"

    def scrape(self, session=None, start=None, end=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using latest")

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

        url = "http://mgaleg.maryland.gov/mgawebsite/Meetings/Day/{}{}?budget=show&cmte=allcommittees&updates=show&ys={}rs"
        url = url.format(start_date, end_date, session)

        page = self.lxmlize(url)
        for row in page.xpath('//div[@id="divAllHearings"]/hr'):
            meta = row.xpath('preceding-sibling::div[contains(@class,"hearsched-hearing-header")]')[-1]
            data = row.xpath('preceding-sibling::div[contains(@class,"row")]')[-1]
            # com_meta = row.xpath('preceding-sibling::div[div[div[contains(@class,"hearsched-committee-banner")]]]')[-1]
            # print(meta.text_content().strip())
            # print("--data--")
            # print(data.text_content().strip())
            # # print(com_meta.text_content().strip())
            # print("--break--")

            when = meta.xpath('.//div[contains(@class,"font-weight-bold text-center")]/text()')[0].strip()

            com_row = meta.xpath('.//div[contains(@class,"font-weight-bold text-center")]/text()')[1].strip()
            time_loc =  meta.xpath(
                './/div[contains(@class,"font-weight-bold text-center")'
                'and (contains(text(),"AM") or contains(text(),"PM"))]/text()'
            )[0].strip()

            time = time_loc.split("-")[0].strip()
            where = time_loc.split("-")[1].strip()

            when = dateutil.parser.parse(f"{when} {time}")
            when = self._tz.localize(when)

            event = Event(
                name=com_row,
                location_name=where,
                start_date=when,
                classification="committee-meeting",
            )

            event.add_source('https://mgaleg.maryland.gov/mgawebsite/Meetings/Week/')

            for agenda_row in data.xpath("div/div/div[contains(@class,'hearsched-table')]"):
                children = agenda_row.xpath('div')
                # bill row
                if len(children) == 4:
                    agenda = event.add_agenda_item(agenda_row.xpath('div[4]/text()')[0].strip())
                    bill_num = agenda_row.xpath('div[1]/a/text()')[0].strip()
                    agenda.add_bill(bill_num)
                    print(bill_num, agenda)
                elif len(children) == 1:
                    agenda = event.add_agenda_item(agenda_row.xpath('div[1]')[0].text_content().strip())
                    print(agenda)

            print(when, com_row, time_loc)
            print("--break--")
            yield event
            sys.exit()
        yield {}
