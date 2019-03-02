import pytz
import lxml
import dateutil.parser
import datetime
import re

from urllib.parse import urlsplit, parse_qs
from openstates.utils import LXMLMixin
from pupa.scrape import Scraper, Event


class MDEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone('US/Eastern')
    chambers = {'upper': 'Senate', 'lower': ''}
    date_format = "%B  %d, %Y"

    def scrape(self, chamber=None, start=None, end=None):
        if start is None:
            start_date = datetime.datetime.now().strftime(self.date_format)
        else:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
            start_date = start_date.strftime(self.date_format)

        # default to 30 days if no end
        if end is None:
            dtdelta = datetime.timedelta(days=30)
            end_date = datetime.datetime.now() + dtdelta
            end_date = end_date.strftime(self.date_format)
        else:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
            end_date = end_date.strftime(self.date_format)

        url = 'http://mgaleg.maryland.gov/webmga/frmHearingSchedule.aspx?&range={} - {}'
        url = url.format(start_date, end_date)

        page = self.lxmlize(url)

        if chamber is None:
            yield from self.scrape_chamber(page, 'upper')
            yield from self.scrape_chamber(page, 'lower')
        else:
            yield from self.scrape_chamber(page, chamber)

    def scrape_chamber(self, page, chamber):
        xpath = '//div[@id="ContentPlaceHolder1_div{}SingleColumn"]/div'.format(self.chambers[chamber])
        com = None
        rows = page.xpath(xpath)

        for row in rows:
            css = row.xpath("@class")[0]
            if 'CommitteeBanner' in css:
                com = row.xpath('string(.//h3/a[1])').strip()
            elif 'CmteInfo' in css or 'DayPanelSingleColumn' in css:
                yield from self.parse_div(row, chamber, com)

    def parse_div(self, row, chamber, com):
        cal_link = row.xpath('.//a[.//span[@id="calendarmarker"]]/@href')[0]
        # event_date = row.xpath('string(.//div[contains(@class,"ItemDate")])').strip()
        title, location, start_date, end_date = self.parse_gcal(cal_link)

        event = Event(
            start_date=start_date,
            end_date=end_date,
            name=title,
            location_name=location,
        )

        event.add_source('http://mgaleg.maryland.gov/webmga/frmHearingSchedule.aspx')

        for item in row.xpath('.//div[@class="col-xs-12a Item"]'):
            description = item.xpath('string(.)').strip()
            agenda = event.add_agenda_item(description=description)

        for item in row.xpath('.//div[contains(@class,"ItemContainer")]/a'):
            description = item.xpath('string(.)').strip()
            agenda = event.add_agenda_item(description=description)

            event.add_document(
                description,
                item.xpath('@href')[0],
                media_type="application/pdf",
                on_duplicate="ignore"
            )

        for item in row.xpath('.//div[contains(@class,"ItemContainer")][./div[@class="col-xs-1 Item"]]'):
            description = item.xpath('string(.)').strip()
            agenda = event.add_agenda_item(description=description)

            bill = item.xpath('.//div[@class="col-xs-1 Item"]/a/text()')[0].strip()
            agenda.add_bill(bill)


        if 'subcommittee' in title.lower():
            subcom = title.split('-')[0].strip()
            print(subcom)
            event.add_participant(
                subcom,
                type='committee',
                note='host',
            )
        else:
            event.add_participant(
                com,
                type='committee',
                note='host',
            )
        yield event

    # Due to the convoluted HTML, it's easier just to parse the google cal links
    def parse_gcal(self, url):
        query = urlsplit(url).query
        params = parse_qs(query)

        dates = params['dates'][0].split('/')

        start_date = self._TZ.localize(
            dateutil.parser.parse(
                dates[0]
            )
        )
        end_date = self._TZ.localize(
            dateutil.parser.parse(
                dates[1]
            )
        )

        return params['text'][0], params['location'][0], start_date, end_date
